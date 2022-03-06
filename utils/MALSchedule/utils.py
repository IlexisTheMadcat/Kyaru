def convert_list_iterator(iterator) -> list:
    new_list = [i for i in iterator]
    while "\n" in new_list:
        new_list.remove("\n")

    return new_list