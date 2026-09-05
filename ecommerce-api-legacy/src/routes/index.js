const { Router } = require('express');
const checkoutRoutes = require('./checkoutRoutes');
const reportRoutes = require('./reportRoutes');
const userRoutes = require('./userRoutes');

const router = Router();

router.use('/api', checkoutRoutes);
router.use('/api', reportRoutes);
router.use('/api', userRoutes);

module.exports = router;
