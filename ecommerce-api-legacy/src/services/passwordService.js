const bcrypt = require('bcryptjs');

const SALT_ROUNDS = 10;

async function hash(password) {
    return bcrypt.hash(password, SALT_ROUNDS);
}

async function compare(password, hashedPassword) {
    return bcrypt.compare(password, hashedPassword);
}

module.exports = { hash, compare };
