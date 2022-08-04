class User:
    all_users = dict()

    def __init__(self, user_id):
        self.city = None
        self.city_id = None
        self.hotels_count = None
        self.user_command = None
        self.check_in = None
        self.check_out = None
        self.block_choose_date = False
        self.sort_flag = 'ASC'
        self.hotel_data = []
        self.need_to_get_ranges_flag = False
        self.p_range = None
        self.d_range = None

        User.add_user(user_id, self)

    @staticmethod
    def get_user(user_id):
        if User.all_users.get(user_id) is None:
            new_user = User(user_id)
            return new_user
        return User.all_users.get(user_id)

    @classmethod
    def add_user(cls, user_id, user):
        cls.all_users[user_id] = user

    @staticmethod
    def del_user(user_id):
        if User.all_users.get(user_id) is not None:
            del User.all_users[user_id]
