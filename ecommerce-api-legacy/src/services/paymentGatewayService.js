const { PAYMENT_STATUS } = require('../constants/paymentStatus');

const APPROVED_CARD_PREFIX = '4';

function charge(cardNumber) {
    const status = cardNumber.startsWith(APPROVED_CARD_PREFIX)
        ? PAYMENT_STATUS.PAID
        : PAYMENT_STATUS.DENIED;

    return { status };
}

module.exports = { charge };
