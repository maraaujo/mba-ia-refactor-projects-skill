const { Router } = require('express');
const reportController = require('../controllers/reportController');
const adminAuth = require('../middleware/adminAuth');

const router = Router();

router.get('/admin/financial-report', adminAuth, reportController.getFinancialReport);

module.exports = router;
