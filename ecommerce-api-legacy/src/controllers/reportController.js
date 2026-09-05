const reportService = require('../services/reportService');
const asyncHandler = require('../utils/asyncHandler');

const getFinancialReport = asyncHandler(async (req, res) => {
    const report = await reportService.getFinancialReport(req.app.locals.db);
    res.json(report);
});

module.exports = { getFinancialReport };
