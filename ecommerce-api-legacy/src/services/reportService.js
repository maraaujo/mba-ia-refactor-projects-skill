const reportModel = require('../models/reportModel');
const { PAYMENT_STATUS } = require('../constants/paymentStatus');

async function getFinancialReport(db) {
    const rows = await reportModel.financialSummary(db);
    const coursesById = new Map();

    for (const row of rows) {
        if (!coursesById.has(row.course_id)) {
            coursesById.set(row.course_id, {
                course: row.course_title,
                revenue: 0,
                students: [],
            });
        }

        if (row.enrollment_id == null) continue;

        const courseData = coursesById.get(row.course_id);

        if (row.payment_status === PAYMENT_STATUS.PAID) {
            courseData.revenue += row.payment_amount || 0;
        }

        courseData.students.push({
            student: row.student_name || 'Unknown',
            paid: row.payment_amount || 0,
        });
    }

    return Array.from(coursesById.values());
}

module.exports = { getFinancialReport };
