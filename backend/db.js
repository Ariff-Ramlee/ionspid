const { Pool } = require('pg');

const pool = new Pool({
  user: 'ionspid_user',
  host: 'localhost',       // or server IP if remote
  database: 'ionspid_db',
  password: 'password',
  port: 5432,              // default PostgreSQL port
});

pool.connect()
  .then(() => console.log('✅ Connected to PostgreSQL'))
  .catch(err => console.error('❌ Connection error', err.stack));

module.exports = pool;
