const passwordService = require('../services/passwordService');
const { PAYMENT_STATUS } = require('../constants/paymentStatus');

async function seed(db) {
    const passwordHash = await passwordService.hash('123');

    const user = await db.run(
        'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
        ['Leonan', 'leonan@fullcycle.com.br', passwordHash]
    );

    const cleanArchitectureCourse = await db.run(
        'INSERT INTO courses (title, price, active) VALUES (?, ?, 1)',
        ['Clean Architecture', 997.0]
    );
    await db.run(
        'INSERT INTO courses (title, price, active) VALUES (?, ?, 1)',
        ['Docker', 497.0]
    );

    const enrollment = await db.run(
        'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
        [user.lastID, cleanArchitectureCourse.lastID]
    );

    await db.run(
        'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
        [enrollment.lastID, 997.0, PAYMENT_STATUS.PAID]
    );
}

module.exports = { seed };
