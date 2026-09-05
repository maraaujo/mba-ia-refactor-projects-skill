const AppError = require('../utils/AppError');
const { config } = require('../config/env');

function adminAuth(req, res, next) {
    const providedKey = req.header('x-admin-key');

    if (!config.adminApiKey || providedKey !== config.adminApiKey) {
        return next(new AppError('Não autorizado', 401));
    }

    next();
}

module.exports = adminAuth;
