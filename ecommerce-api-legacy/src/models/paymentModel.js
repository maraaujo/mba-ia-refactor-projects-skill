async function create(db, { enrollmentId, amount, status }) {
    const result = await db.run(
        'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
        [enrollmentId, amount, status]
    );
    return result.lastID;
}

async function deleteByEnrollmentId(db, enrollmentId) {
    return db.run('DELETE FROM payments WHERE enrollment_id = ?', [enrollmentId]);
}

module.exports = { create, deleteByEnrollmentId };
