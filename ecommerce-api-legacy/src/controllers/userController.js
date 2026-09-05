const userService = require('../services/userService');
const asyncHandler = require('../utils/asyncHandler');

const deleteUser = asyncHandler(async (req, res) => {
    const { id } = req.params;
    await userService.deleteUser(req.app.locals.db, id);
    res.send('Usuário deletado com sucesso.');
});

module.exports = { deleteUser };
