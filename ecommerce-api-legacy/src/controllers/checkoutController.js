const checkoutService = require('../services/checkoutService');
const asyncHandler = require('../utils/asyncHandler');

const checkout = asyncHandler(async (req, res) => {
    const { usr, eml, pwd, c_id, card } = req.body;

    if (!usr || !eml || !c_id || !card) {
        return res.status(400).send('Bad Request');
    }

    const result = await checkoutService.checkout(req.app.locals.db, {
        username: usr,
        email: eml,
        password: pwd,
        courseId: c_id,
        cardNumber: card,
    });

    res.status(200).json({ msg: 'Sucesso', enrollment_id: result.enrollmentId });
});

module.exports = { checkout };
