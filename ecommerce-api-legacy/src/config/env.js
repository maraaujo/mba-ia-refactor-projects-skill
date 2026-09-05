require('dotenv').config();

const config = {
    port: parseInt(process.env.PORT, 10) || 3000,
    databaseUrl: process.env.DATABASE_URL || ':memory:',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
    adminApiKey: process.env.ADMIN_API_KEY || '',
};

module.exports = { config };
