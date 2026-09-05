const sqlite3 = require('sqlite3').verbose();
const { config } = require('../config/env');
const Database = require('./Database');

function createConnection() {
    return new Promise((resolve, reject) => {
        const sqliteDb = new sqlite3.Database(config.databaseUrl, (err) => {
            if (err) return reject(err);
            resolve(new Database(sqliteDb));
        });
    });
}

module.exports = { createConnection };
