function errorHandler(err, req, res, next) {
    const statusCode = err.statusCode || 500;
    const message = err.statusCode ? err.message : 'Erro interno do servidor';

    if (!err.statusCode) {
        console.error(err);
    }

    res.status(statusCode).send(message);
}

module.exports = errorHandler;
