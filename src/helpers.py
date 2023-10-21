def GetPotionRecipeFromName(name):
    """Returns the recipe of the potion from the name."""
    if name == "red":
        return [100, 0 , 0, 0]
    elif name == "green":
        return [0, 100, 0, 0]
    elif name == "blue":
        return [0, 0 , 100, 0]
    elif name == "dark":
        return [0, 0, 0, 100]
    
def GetRecipeNameFromIndex(index):
    if index == 0:
        return "red"
    elif index == 1:
        return "green"
    elif index == 2:
        return "blue"
    elif index == 3:
        return "dark"
    
def GetNameFromRecipe(recipe):
    """Returns the name of the potion from the recipe."""
    if recipe == [1, 0 , 0, 0]:
        return "red"
    elif recipe == [0, 1, 0, 0]:
        return "green"
    elif recipe == [0, 0 , 1, 0]:
        return "blue"
    elif recipe == [0, 0, 0, 1]:
        return "dark"
    return None


barrelSize = {"MINI" : 0, "SMALL" : 1, "MEDIUM" : 2, "LARGE" : 3}

def GetBarrelType(sku):
    label = sku.split("_")[0]
    return barrelSize[label]