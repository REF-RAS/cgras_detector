

overlap_sets_list = []

overlap_sets_list.append(set((0, 1, 2)))
overlap_sets_list.append(set((3, 4)))

object_1_set = [s for s in overlap_sets_list if 5 in s]
object_2_set = [s for s in overlap_sets_list if 36 in s]
object_1_set = object_1_set[0] if object_1_set else None
object_2_set = object_2_set[0] if object_2_set else None
                
print(object_1_set == object_2_set)

print(set((1, 2, 3)) == set((1, 2, 4)))