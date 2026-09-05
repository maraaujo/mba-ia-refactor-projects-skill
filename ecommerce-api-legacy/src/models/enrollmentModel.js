async function create(db, { userId, courseId }) {
    const result = await db.run(
        'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
        [userId, courseId]
    );
    return result.lastID;
}

async function findByUserId(db, userId) {
    return db.all('SELECT * FROM enrollments WHERE user_id = ?', [userId]);
}

async function deleteByUserId(db, userId) {
    return db.run('DELETE FROM enrollments WHERE user_id = ?', [userId]);
}

module.exports = { create, findByUserId, deleteByUserId };
