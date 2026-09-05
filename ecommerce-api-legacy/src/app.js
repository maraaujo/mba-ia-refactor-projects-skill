const express = require('express');
const { config } = require('./config/env');
const { createConnection } = require('./database/connection');
const { initSchema } = require('./database/schema');
const { seed } = require('./database/seed');
const routes = require('./routes');
const errorHandler = require('./middleware/errorHandler');

async function bootstrap() {
    const app = express();
    app.use(express.json());

    const db = await createConnection();
    await initSchema(db);
    await seed(db);

    app.locals.db = db;

    app.use(routes);
    app.use(errorHandler);

    app.listen(config.port, () => {
        console.log(`Frankenstein LMS rodando na porta ${config.port}...`);
    });
}

bootstrap().catch((err) => {
    console.error('Falha ao iniciar aplicação:', err);
    process.exit(1);
});
