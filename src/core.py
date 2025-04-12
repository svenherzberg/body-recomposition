class Recipe:
    def __init__(self, id, name, calories, protein, fat, carbs):
        self.id = id
        self.name = name
        self.calories = calories
        self.protein = protein
        self.fat = fat
        self.carbs = carbs

        self.ingredients = list()
        self.recipe = None


    def get_nutrition(self):
        return self.calories, self.protein, self.fat, self.carbs

    def calculate_macros(self):
        """
        calculates macros from the self.ingredients
        :return:
        """
        calories, protein, fat, carbs = None, None, None, None
        # ToDo: implement calculation
        return calories, protein, fat, carbs

    def update_macros(self):
        self.calories, self.protein, self.fat, self.carbs = self.calculate_macros()


class Cookbook():
    def __init__(self):
        self.recipes = list()

    def list_recipes(self):
        for recipe in self.recipes:
            print('| ', recipe.id, ' | ', recipe.name, ' |') # das geht besser mit formatiertem print


class DayMealPlanning:
    def __init__(self):
        self.meals = []
        self.calories = 0
        self.protein = 0
        self.fat = 0
        self.carbs = 0

    def add_meal(self, meal: Recipe):
        self.meals.append(meal)

    def add_meal_from_cookbook(self, cookbook: Cookbook, id=None, name=None):
        assert cookbook is not None, 'Cookbook not provided'
        assert len(cookbook.recipes) > 0, 'Cookbook does not contain recipes'
        assert not( id is None and name is None), 'Choose recipe by id or name'
        if id is not None:
            for recipe in cookbook.recipes:
                if recipe.id == id:
                    self.add_meal(meal=recipe)
        elif name is not None:
            for recipe in cookbook.recipes:
                if recipe.name == name:
                    self.add_meal(meal=recipe)
        self.recalculate_macros()

    def recalculate_macros(self):
        self.calories, self.protein, self.fat, self.carbs = 0, 0, 0, 0
        for meal in self.meals:
            self.calories += meal.calories
            self.protein += meal.protein
            self.fat += meal.fat
            self.carbs += meal.carbs

    def get_macros(self):
        self.recalculate_macros()
        return self.calories, self.protein, self.fat, self.carbs

    def get_macro_percentages(self):
        calories, protein, fat, carbs = self.get_macros()
        return protein*4/calories, fat*9/calories, carbs*4/calories

    def show_macros(self):
        self.recalculate_macros()
        print(f'Calories {self.calories} Protein {self.protein} Fat {self.fat} Carbs {self.carbs}')



class WeekMealPlanning:
    def __init__(self):
        self.weekdays = list()


def load_recipes():
    import recipes
    return recipes.recipes


def initialize_cookbook():
    recipes_raw = load_recipes()
    cookbook = Cookbook()
    for id, recipe_raw in enumerate(recipes_raw):
        name, calories, protein, fat, carbs = recipe_raw['name'], recipe_raw['calories'], recipe_raw['protein'], recipe_raw['fat'], recipe_raw['carbs']
        recipe = Recipe(id, name, calories, protein, fat, carbs)
        cookbook.recipes.append(recipe)
    return cookbook


cookbook = initialize_cookbook()
monday = DayMealPlanning()

cookbook.list_recipes()

print('Add meals to your day, by using add_meal_from_cookbook.')
print('Calculate Macros by using calculate_macros.')


def get_meal_combinations(cookbook, number_meals, minimum_protein=120, calories_lower=1600, calories_upper=1750):
    from itertools import combinations

    print(f'### Number of Meals: {number_meals} ################################')

    cnt = 1
    meal_combination_codes = list()
    for meal_ids in combinations(range(len(cookbook.recipes)), number_meals):
        if 0 not in set(meal_ids):
            continue
        if set(meal_ids).intersection(set({3, 12})):
            continue
        day = DayMealPlanning()
        for meal_id in meal_ids:
            day.add_meal_from_cookbook(cookbook, meal_id)
        calories, protein, fat, carbs = day.get_macros()
        if calories < calories_lower:
            continue
        if calories > calories_upper:
            continue
        if protein < minimum_protein:
            continue
        meal_combination_codes.append(meal_ids)
        print(f'\n*** Recipe Combination # {cnt} ***********************************')
        day.show_macros()
        for meal in day.meals:
            print(meal.name)
        cnt += 1
    return meal_combination_codes


#meal_combination_codes_3 = get_meal_combinations(cookbook, 3)
#cnt1 = len(meal_combination_codes_3)
#print(f'Es gibt {cnt1} verschiedene Varianten mit 3 Mahlzeiten')
meal_combination_codes_4 = get_meal_combinations(cookbook, 4)
cnt2 = len(meal_combination_codes_4)
print(f'Es gibt {cnt2} verschiedene Varianten mit 4 Mahlzeiten')

#print(cnt1, cnt2, cnt1 + cnt2)




