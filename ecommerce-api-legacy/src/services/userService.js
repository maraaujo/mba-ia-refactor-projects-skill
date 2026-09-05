const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');

async function deleteUser(db, userId) {
    const enrollments = await enrollmentModel.findByUserId(db, userId);

    for (const enrollment of enrollments) {
        await paymentModel.deleteByEnrollmentId(db, enrollment.id);
    }

    await enrollmentModel.deleteByUserId(db, userId);
    await userModel.deleteById(db, userId);
}

module.exports = { deleteUser };
