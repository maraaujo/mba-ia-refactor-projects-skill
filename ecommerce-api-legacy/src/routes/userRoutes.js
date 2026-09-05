const { Router } = require('express');
const userController = require('../controllers/userController');
const adminAuth = require('../middleware/adminAuth');

const router = Router();

router.delete('/users/:id', adminAuth, userController.deleteUser);

module.exports = router;
