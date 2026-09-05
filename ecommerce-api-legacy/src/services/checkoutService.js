const userModel = require('../models/userModel');
const courseModel = require('../models/courseModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');
const auditLogModel = require('../models/auditLogModel');
const passwordService = require('./passwordService');
const paymentGatewayService = require('./paymentGatewayService');
const { PAYMENT_STATUS } = require('../constants/paymentStatus');
const AppError = require('../utils/AppError');

async function checkout(db, { username, email, password, courseId, cardNumber }) {
    const course = await courseModel.findActiveById(db, courseId);
    if (!course) throw new AppError('Curso não encontrado', 404);

    const existingUser = await userModel.findByEmail(db, email);
    let userId;

    if (existingUser) {
        userId = existingUser.id;
    } else {
        if (!password) throw new AppError('Senha obrigatória para novo usuário', 400);
        const passwordHash = await passwordService.hash(password);
        userId = await userModel.create(db, { name: username, email, passwordHash });
    }

    const { status } = paymentGatewayService.charge(cardNumber);
    if (status === PAYMENT_STATUS.DENIED) {
        throw new AppError('Pagamento recusado', 400);
    }

    const enrollmentId = await enrollmentModel.create(db, { userId, courseId });
    await paymentModel.create(db, { enrollmentId, amount: course.price, status });
    await auditLogModel.create(db, `Checkout curso ${courseId} por ${userId}`);

    return { enrollmentId };
}

module.exports = { checkout };
