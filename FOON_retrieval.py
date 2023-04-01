'''
FOON: Retrieval Methods (FOON_retrieval):
        (last updated: 21st April, 2022):
-------------------------------------------
-- Written and maintained by: 
    * David Paulius (davidpaulius@usf.edu / dpaulius@cs.brown.edu)
    * Md Sadman Sakib (mdsadman@usf.edu)

NOTE: If using this program and/or annotations provided by our lab, please kindly cite our papers
    so that others may find our work:
* Paulius et al. 2016 - https://ieeexplore.ieee.org/abstract/document/7759413/
* Paulius et al. 2018 - https://ieeexplore.ieee.org/abstract/document/8460200/

'''
import collections, time, getopt, ast, tqdm, itertools as IT, os, sys

import FOON_classes as FOON

last_updated = '21st April, 2022'

###############################################################################################################################

# NOTE: the following are parameters or variables that are needed to operate the retrieval process:

# -- depth :- maximum depth to search for task tree:
#   -- you can change this to a larger number if diameter of FOON is large.
depth = 25

# -- verbose flag to print any extra comments or prompts for debugging:
verbose = False

# NOTE: parameters for the retrieval process:
# -- goal_object_type :- object type (i.e., ID number) of the goal object
# -- goal_state_type :- state type(s) (i.e., ID number(s)) of the goal object, given as list of integers!
# -- search_level :- hierarchy level to perform the searching operation
goal_object_type, goal_state_type = None, None
search_level = None

# NOTE: retrieval_method: 1 (task tree retrieval) or 2 (path tree retrieval)
# -- more on task tree retrieval can be found here: https://arxiv.org/abs/1902.01537
# -- more on path tree retrieval can be found here: https://arxiv.org/abs/1905.00502
retrieval_method = None			

# NOTE: dictionary or list references for structures loaded by FGA:
FOON_functionalUnits, FOON_nodes, FOON_outputsToUnits, FOON_objectsToUnits, FOON_functionalUnitMap = None, None, None, None, None
FOON_objectLabels, FOON_motionLabels, FOON_stateLabels = {}, {}, {}

###############################################################################################################################

def _copyDicts(data):
    # NOTE: in Python, global variables are only global within the scope of a module (i.e., file);
    # 	therefore, this function is used to bypass that by copying references from FGA for the necessary lists or dictionaries for search.

    # -- assigning references from FGA to the FRT module:
    global goal_object_type, goal_state_type
    if 'goal_object_type' in data and 'goal_state_type' in data:
        goal_object_type, goal_state_type = data['goal_object_type'], data['goal_state_type']

    global FOON_functionalUnits, FOON_nodes, FOON_outputsToUnits, FOON_objectsToUnits, FOON_functionalUnitMap
    FOON_functionalUnits = data['fu_list']
    FOON_nodes = data['nodes_list']
    FOON_outputsToUnits = data['outputs_to_fu']
    FOON_objectsToUnits = data['objs_to_fu']
    FOON_functionalUnitMap = data['fu_to_fu']

    # -- assigning references to labels read from index files:
    global FOON_objectLabels, FOON_motionLabels, FOON_stateLabels
    if 'labels' in data:
        FOON_objectLabels = data['labels']['objects']
        FOON_motionLabels = data['labels']['motions']
        FOON_stateLabels = data['labels']['states']
#enddef


def _startRetrieval():
    print("-- [FOON_retrieval] : Preparing task tree retrieval..")

    global goal_object_type, goal_state_type, search_level, retrieval_method

    # -- if the goal's object and state IDs are not given as arguments, provide them with the following options to do so:
    if goal_object_type == None or goal_state_type == None:
        _response = input(' -- Would you like to look up objects and states by name? [Y/N] (default: N) > ')
        if _response.lower() == 'y':
            # -- this is if the user does not know the ID numbers off-hand:
            goal_object_type, goal_state_type = _searchGoalByName()
        #endif
    #endif

    if goal_object_type == None or goal_state_type == None:
        # -- this is if you know what the object and state IDs are:
        goal_object_type = int(input(" -- Enter the OBJECT type (i.e., ID -- an INTEGER) to be searched: > "))
        goal_state_type = ast.literal_eval(input(" -- Enter the OBJECT state(s) in the form of a list of INTEGER IDs (e.g., '[1,33,7]'): > "))
    #endif

    if not search_level:
        _response = input(" -- At what level is the search being done? [1/2/3] (default: 3) > ")

        # -- by default, do everything at level 3 hierarchy:
        if _response == '1':
            search_level = 1
        elif _response == '2':
            search_level = 2
        else:
            search_level = 3
        #endif
    #endif

    if not retrieval_method:
        _response = input(" -- Would you like to perform: 1) greedy or 2) optimal retrieval? [1/2] (default: 1) > ")
        
        retrieval_method = 1
        if _response == '2':
            retrieval_method = 2
        #endif
    #endif

    result = None
    if retrieval_method == 2:
        result = _pathTreeRetrieval(goal_object_type, goal_state_type, search_level)
    else:
        result = _taskTreeRetrieval_greedy(goal_object_type, goal_state_type, search_level)
    #endif

    return result
#enddef


def _searchGoalByName():
    global FOON_objectLabels, FOON_stateLabels

    if not FOON_objectLabels or not FOON_stateLabels:
        print('ERROR: Cannot perform goal name search without loading labels from index file!')
        return None, None

    # -- using existing string distance metrics from either 'jellyfish' or 'NLTK' to find closest object/state labels;
    #	this will make it easier for people to initialize a search via name rather than knowing or providing integer IDs
    try:
        from jellyfish import jaro_winkler_similarity
    except ImportError:
        print("WARNING: Module 'jellyfish' is not installed! Now trying to import from 'NLTK'...")
    try:
        from nltk.metrics.distance import jaro_winkler_similarity
    except ImportError:
        print("WARNING: Module 'NLTK' is also not installed! Please install one of these to use this function.")
        return

    # -- Prompting for the object name:
    option, selection = 0, None
    while option == 0:
        search_results = []

        _response = input(' -- Please type the name of an OBJECT you would like for the goal object: > ')
        for key in FOON_objectLabels:
            if jaro_winkler_similarity(_response, key) > 0.75:
                search_results.append( [key, FOON_objectLabels[key]] )

        # -- sort results in alphabetical order:
        search_results.sort()

        if len(search_results) > 0:
            print(' -- Closest object labels are as follows:')
            for res in search_results:
                print('   ' + str(search_results.index(res) + 1) + ' - ' + str(res[0]))
            option = int(input('   Enter INTEGER preceding the suitable label to select it or enter 0 (zero) to start over : > '))
            if option > 0:
                selection = search_results[option-1]
        else:
            print(" -- No objects found that are close enough to '" + _response + "'!")
    #end
    
    # -- object ID will be the second element of the selection result:
    object_id = selection[1]

    # -- Prompting for the object's state name:
    option, selection = 0, []
    while option == 0:
        search_results = []

        _response = input(' -- Please type the name or phrase for an object STATE you would like for the goal object: > ')
        for key in FOON_stateLabels:
            if jaro_winkler_similarity(_response, key) > 0.65:
                search_results.append( [key, FOON_objectLabels[key]] )

        # -- sort results in alphabetical order:
        search_results.sort()

        if len(search_results) > 0:
            print(' -- Closest state labels are as follows:')
            for res in search_results:
                print('   ' + str(search_results.index(res) + 1) + ' - ' + str(res[0]))
            option = int(input('   Enter INTEGER preceding the suitable label to select it or enter 0 (zero) to start over : > '))
            if option > 0:
                selection.append(search_results[option-1])
        else:
            print(" -- No state found that is close enough to '" + _response + "'!")

        print(' -- Repeating search (in case of multiple states)...')
    #end

    # -- just as with objects, state IDs will be the second element in each sub-array:
    state_ids = [state[1] for state in selection]

    return object_id, state_ids
#enddef

###############################################################################################################################

def _findNodes_InputOnly():
    inputs_only = []
    if verbose:
        print("\n-- Default input nodes:")

    # -- checking for starting nodes based on lack of functional units that contain them as output nodes:
    for _node in FOON_outputsToUnits[2]:
        is_input = False
        if _isStartingNode(_node):
            # -- a starting node can be a node which is never an output node:
            is_input = True

        else:
            # -- we may also have nodes that are featured as both input and output, 
            #       but they are in states which are primarily seen among input-only nodes:
            for FU in FOON_objectsToUnits[2][_node]:
                if _node in FU.getInputNodes():
                    is_input = True
                    break

            is_input = _isBaseState(_node) and is_input
        #endif

        if is_input:
            inputs_only.append(_node)
            if verbose:
                _node.print_functions[2]()
        #end
    #endfor

    return inputs_only
#enddef


def _createFile_InputOnly():
    inputs_only = _findNodes_InputOnly()
    _file = open('FOON-input_only_nodes.txt', 'w')
    for _object in inputs_only:
        _file.write(_object.getObjectText() + "\n")
    #endfor
    _file.close()	# -- Don't forget to close the file once we are done!
#enddef


def _createFile_OutputOnly():
    outputs_only = _findNodes_OutputOnly()
    _file = open('FOON-output_only_nodes.txt', 'w')
    for _object in outputs_only:
        _file.write(_object.getObjectText() + "\n")
    #endfor
    _file.close()	# -- Don't forget to close the file once we are done!
#enddef


def _loadKitchenList(file='FOON-input_only_nodes.txt'):
    # NOTE: kitchen items refer to nodes that are either:
    #	1) input only nodes (by default);
    #	2) nodes that will not be expanded in the search process.

    try:
        _file = open(file, 'r') 
    except Exception:
        # -- this means that no file exists, so just default to creating a file with purely input nodes:
        print(' -- [FOON_retrieval] : Creating file with kitchen items...')
        _createFile_InputOnly()
        _file = open('FOON-input_only_nodes.txt', 'r') 
    #endtry

    # -- split the file into lines and then do parsing as we would for a regular FOON graph file:
    items = _file.read().splitlines()

    kitchen = []
    kitchenObject = None

    for line in items:
        if line.startswith("O"):
            # -- we have an Object already in consideration which we were appending states to:
            if kitchenObject:
                kitchen.append(kitchenObject)
            # -- this is an Object node, so we probably should read the next line one time
            # -- get the Object identifier by splitting first instance of O
            objectParts = line.split("O"); objectParts = objectParts[1].split("\t")

            # -- create a new object which is equal to the kitchenObject and add it to the list:
            kitchenObject = FOON.Object(objectID=int(objectParts[0]), objectLabel=objectParts[1])

        elif line.startswith("S"):
            # -- get the Object's state identifier by splitting first instance of S
            stateParts = line.split("S"); stateParts = stateParts[1].split("\t"); stateParts = list(filter(None, stateParts))

            # -- check if this object is a container or has geometrically-relative object:
            relative_object = None; list_ingredients = []
            if len(stateParts) > 2:
                if '{' in stateParts[2]:
                    # NOTE: all ingredients are enclosed in curly brackets:
                    ingredients = [ stateParts[2] ]
                    ingredients = ingredients[0].split("{")
                    ingredients = ingredients[1].split("}")

                    # -- we then need to make sure that there are ingredients to be read.
                    if len(ingredients) > 0:
                        ingredients = ingredients[0].split(",")
                        for I in ingredients:
                            list_ingredients.append(I)
                elif '[' in stateParts[2]:
                    # NOTE: a geometrically-relative object (relater - not a good name) is enclosed in square brackets:

                    # -- mention of geometrically-relative object:
                    relater = [ stateParts[2] ]
                    relater = relater[0].split("[")
                    relater = relater[1].split("]")
                    relative_object = relater[0]
                else:
                    print(' -- WARNING: possibly incorrect or unexpected extra entry in line ' + str(items.index(line)) + '? > ' + str(stateParts[2]))
                    pass

            kitchenObject.addNewState([int(stateParts[0]), stateParts[1], relative_object])

            if list_ingredients:
                kitchenObject.setIngredients(list_ingredients)

        else:
            pass
    #endfor

    # -- append the last object that would not have been saved in the last iteration:
    kitchen.append(kitchenObject)

    _file.close()	# -- Don't forget to close the file once we are done!

    return kitchen
#enddef


def _isStartingNode(O):
    # NOTE: simple function to evaluate whether a certain node is a starting node:

    # -- one surefire way: check the output node to functional unit map; 
    # 	a node that is a starting node will be mapped to an empty list of functional units:
    procedures = FOON_outputsToUnits[2].get(O)
    if not procedures:
        return True

    return False
#enddef


def _isBaseState(O):
    # -- another possibility: what if this node has starting node states?
    #	(e.g. 'empty', 'off', 'clean') 
    count_initial_states = 0
    for S in range(len(O.getStatesList())):
        if O.getStateLabel(S) in ['empty', 'off', 'off (ready)', 'clean', 'whole', 'unpeeled', 'clove']:
            count_initial_states += 1
        
    # --  a starting node will only have the preceding starting/initial states:
    if count_initial_states == len(O.getStatesList()):
        return True

    # -- if it passes these conditions, then we can say that it is not a starting node:
    return False
#enddef


def _findNodes_OutputOnly():
    global verbose; outputs_only = []
    if verbose:
        print("\n-- Default output nodes:")

    for _node in FOON_outputsToUnits[2]:
        procedures = FOON_outputsToUnits[2].get(_node)
        if procedures:
            outputs_only.append(_node)
            if verbose:
                _node.print_functions[2]()
    #endfor
    return outputs_only
#enddef

###############################################################################################################################

# NOTE: the following are retrieval related functions:
# -- task tree retrieval -> find a single task tree / path that satisfies making a specific goal node:
# -- path tree retrieval -> find all possible paths that satisfy making a specific goal node:

def _taskTreeRetrieval_greedy(goalType, goalState, hierarchy_level=3, environment=None):
    # NOTE: this is the vanilla task tree algorithm from Paulius et al. 2016.
    # -- this algorithm simply finds the first instance of functional units that meets the goal node requirement.
    # -- this algorithm requires a list of ingredients that are found in the robot's environment (provided as a file).

    global verbose, FOON_nodes, FOON_outputsToUnits

    print('\n-- [TASK_TREE] : Loading kitchen (i.e., items in environment) file...')

    # -- sometimes we may define a specific kitchen; other times, we just stick to default:
    if not environment:
        file = input('  -- Please provide the name of the file with KITCHEN ITEMS (press ENTER ONLY to use default): > ')
        if file == '':
            environment = _loadKitchenList() # -- use default 'FOON-input_only_nodes.txt'
        else:
            environment = _loadKitchenList(file) # -- use a different text file with kitchen items
        #endif
    #endif

    # -- create a temporary goal node object which is used to find the exact target in FOON:
    goalNode = FOON.Object(objectID=int(goalType), objectLabel=None)
    for x in goalState:
        goalNode.addNewState([int(x), None, []])
    #endif

    if hierarchy_level == 1:
        searchNodes = FOON_nodes[0]; searchMap = FOON_outputsToUnits[0]
    elif hierarchy_level == 2:
        searchNodes = FOON_nodes[1]; searchMap = FOON_outputsToUnits[1]
    elif hierarchy_level == 3:
        searchNodes = FOON_nodes[2]; searchMap = FOON_outputsToUnits[2]
    else:
        return

    search_level = hierarchy_level
    if search_level == 3:
        search_level = 2	# -- we only consider level 2 nodes if we do not have exact candidate

    # -- we will identify different target goal nodes that have the same object/state combination:
    goals = []

    # NOTE: refer to the search_level description for a run-down of the intuition here:
    index = -1
    for T in searchNodes:
        if isinstance(T, FOON.Object):
            if T.equals_lvl1(goalNode) and T.isSameStates_ID_only(goalNode):
                index = searchNodes.index(T)
                goals.append(searchNodes[index])

    if not goals or index == -1:
        print("Item " + goalNode.getObjectKey(hierarchy_level) + " has not been found in network!")
        return False
    #endif

    print("\n-- [TASK_TREE] : Initializing naive task tree retrieval...")
    print(' -- Pseudocode for this algorithm can be found here: https://arxiv.org/abs/1902.01537')

    if verbose:
        print("\n-- Candidate goal nodes are as follows:")
        for G in goals:
            G.print_functions[hierarchy_level-1]()
    
    if verbose:
        print("\n-- Proceeding with task tree retrieval...\n")

    # -- startNodes - list of object nodes which we have available to the algorithm:
    startNodes = []
    for T in environment:
        index = -1
        for N in searchNodes:
            if isinstance(N, FOON.Object):
                if T.equals_lvl1(N) and T.isSameStates_ID_only(N):
                    index = searchNodes.index(N)
                    break

        if index != -1:
            # -- this means that the object exists in FOON; if not..
            startNodes.append(searchNodes[index])

        else:
            try:
                import FOON_generalization as fgen
            except ImportError:
                pass
            else:	
                # .. we can try to find a substitute for this object:
                possible_substitutes = fgen._findObjectSubstitute(T)

                for P in possible_substitutes:
                    index = -1
                    for N in searchNodes:
                        if P.equals_functions[hierarchy_level-1](N):
                            index = searchNodes.index(N); break
                    #endfor

                    if index > -1:
                        # -- this means that the object exists in FOON; if not..
                        startNodes.append(searchNodes[index])


    for G in goals:
        print("\n-- [TASK_TREE] : Attempting to search for object:")
        G.print_functions[hierarchy_level-1]()
        print(" -----------------------------------")

        if G in startNodes:
            print(' -- WARNING: This object already exists in the kitchen!')
            continue

        # What structures do we need in record keeping?
        #	-- a FIFO list of all nodes we need to search (a queue)
        #	-- a list that keeps track of what we have seen
        #	-- a list of all items we have/know how to make in the present case (i.e. the kitchen list)
        itemsToSearch = collections.deque(); subgoals = {}; kitchen = []

        goalNode = G	# this is the actual goal node which is in the network.

        # -- Add the object we wish to search for to the two lists created above:
        itemsToSearch.append(goalNode)

        # -- generating new kitchen list per object searched (since we may satisfy new subgoals):
        for T in startNodes:
            kitchen.append(T)
        #endfor

        candidates = [] 	# -- structure to keep track of all candidate functional units in FOON
        task_tree = []		# -- tree with all functional units needed to create the goal based on the kitchen items
        all_path_trees = [] 	# -- list of ALL possible functional units that can be used for making the item.

        global depth 	# -- maximum number of times you can "see" the original goal node.
        max_iterations = 0
        endSearch = False	# -- flag that is used to stop searching at goal node G that satisfies retrieval.

        while itemsToSearch:
            # -- Remove the item we are trying to make from the queue of items we need to learn how to make
            tempObject = itemsToSearch.popleft()

            if verbose:
                print('\n -- Object removed from queue:')
                tempObject.print_functions[hierarchy_level-1]()

            # -- sort-of a time-out for the search if it does not produce an answer dictated by the amount of time it takes.
            if tempObject.equals_functions[hierarchy_level-1](goalNode):
                max_iterations += 1
                print('\n -- goal re-encountered = ' + str(max_iterations))

            if tempObject in startNodes:
                continue

            if max_iterations > depth:	# just the worst possible way of doing this, but will do for now.
                endSearch = True
                break

            if goalNode in kitchen:
                break

            if tempObject in kitchen:
                # -- just proceed to next iteration, as we already know how to make current item!
                continue
    
            # -- we need to then identify possible candidate functional units;
            #	candidates are those that contain this current object (i.e. tempObject) in its outputs
            num_candidates = 0
            candidates = list(searchMap.get(tempObject))
            num_candidates = len(candidates)
            all_path_trees += candidates

            if candidates == False:
                # -- this means that there is NO solution to making an object,
                #	and so we just need to add it as something we still need to learn how to make.
                startNodes.append(tempObject)
                continue

            numObjectsAdded = 0
            
            while candidates:
                candidate_FU = candidates.pop() 	# -- remove the first candidate functional unit we found
                count = 0	 			# -- variable to count the number of inputs that we have in the kitchen

                for T in candidate_FU.getInputList():
                    flag = False

                    if T in kitchen:
                        # -- if an input is in the kitchen, then we do not need to search for it:
                        flag = True

                    if flag == False:
                        # -- if an item is not in the "objects found" list, then we add it to the list of items we then need to explore and find out how to make.
                        if T in itemsToSearch:
                            flag = True

                        if flag == False:
                            if tempObject in subgoals:
                                mini_goals = subgoals[tempObject]
                                if T not in mini_goals:
                                    mini_goals.append(T)
                            else:
                                subgoals[tempObject] = [T]

                            itemsToSearch.append(T)
                            numObjectsAdded += 1

                            if verbose:
                                print('\n -- Object added to queue:')
                                T.print_functions[hierarchy_level-1]()
                    else :
                        # -- since this is in the kitchen, we need to account for this:
                        count += 1

                num_candidates -= 1	# -- one less candidate to consider..

                if count == candidate_FU.getNumberOfInputs() and count > 0:
                    # UPDATE: before marking an object as solved, we need to remove other objects in the queue that are not necessary anymore:
                    mini_goals = subgoals.pop(tempObject, None)
                    if mini_goals:
                        for M in mini_goals:
                            itemsToSearch	= collections.deque((filter((M).__ne__, itemsToSearch)))

                    # We will have all items needed to make something;
                    #	add that item to the "kitchen", as we consider it already made.
                    found = False
                    if tempObject in kitchen:
                        found = True

                    if found == False:
                        kitchen.append(tempObject)

                    for T in candidate_FU.getOutputList():
                        #	add that item to the "kitchen", as we consider it already made.
                        found = False
                        if T in kitchen:
                            found = True

                        if found == False:
                            kitchen.append(T)
                    #endfor

                    found = False
                    if candidate_FU in task_tree:
                        found = True

                    if not found:
                        task_tree.append(candidate_FU)

                    # -- since we found a suitable FU, we must remove all other traces of other candidates:
                    for x in range(numObjectsAdded):
                        # -- remove the last items that were added to queue that no longer should be considered!
                        itemsToSearch.popleft()

                    for x in range(num_candidates):
                        # -- remove all functional units that can make an item - we take the first one that works!
                        candidates.pop()

                else:
                    # -- if a solution has not been found yet, add the object back to queue.
                    found = False
                    if tempObject in itemsToSearch:
                        found = True
                    
                    if not found:
                        itemsToSearch.append(tempObject)

        if endSearch:
            print("\n-- [TASK_TREE] : Exceeded allowable depth (max_iterations). Search ended!")

            print(" -- Objects that were found to be missing:")
            print("  -- Starting Nodes:")
            for S in startNodes:
                S.print_functions[hierarchy_level-1]()

            print("\n  -- Nodes remaining in queue:")
            for S in itemsToSearch:
                S.print_functions[hierarchy_level-1]()

            return []

        else:
            print("\n-- [TASK_TREE] : Task tree found!")
            print(" -- Length of task tree found: " + str(len(task_tree)))

            # -- save task tree as a TXT file:
            file_name = "FOON_task-tree-for-" + goalNode.getObjectKey(hierarchy_level) + "_lvl" + str(hierarchy_level) + ".txt"
            _file = open(file_name, 'w')
            for FU in task_tree:
                # -- just write all functional units that were put into the list:
                _file.write(FU.getFunctionalUnitText())
            #endfor
            _file.close()

            # -- save task tree as a JSON file:
            try:
                import json
            except ImportError:
                pass
            else:
                subgraph_units = {}
                subgraph_units['functional_units'] = []

                file_name = "FOON_task-tree-for-" + goalNode.getObjectKey(hierarchy_level) + "_lvl" + str(hierarchy_level) + ".json"
                _file = open(file_name, 'w')
                for FU in task_tree:
                    subgraph_units['functional_units'].append(FU.getFunctionalUnitJSON())
                json.dump(subgraph_units, _file, indent=7)
                _file.close()
            #endtry

            print(" -- Task tree sequence has been saved in file : " + file_name)
            return task_tree

    # -- after exhausting through all possible goal nodes, we just end the search:
    return []
#enddef

def _taskTreeRetrieval_weighted(all_path_trees, goalType, goalState, hierarchy_level):
    from copy import copy
    
    goalNode = FOON.Object(objectID=int(goalType), objectLabel=None)
    for x in goalState:
        goalNode.addNewState([int(x), None, []])

    folder = "path_trees_to_" + goalNode.getObjectKey(hierarchy_level) + "/"
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    # -- this is the total number of human-assisted motions possible.
    max_depth = 0

    for T in all_path_trees:
        M = len(T)

        # -- this is to keep track of the maximum length M possible in all task trees:
        if M > max_depth:
            max_depth = M
    #endfor

    optimal_paths = []

    # Step 4: Determine the highest success rate paths from human-assisted steps 0 to M.
    for M in range(max_depth + 1):
        # NOTE: our goal is to find a path with the highest success rate out of all possible paths for every value of M:
        candidate_paths = []

        for T in all_path_trees:
            if len(T) < M:
                # -- this means that we are checking for a certain value of M that exceeds the entire length of this path.
                continue

            path_sorted = sorted(T)	# -- sort each path first to determine the M lowest success rate FUs.

            temp_path = []
            for FU in T: # -- the FUs in T (path) are unsorted, while they are sorted in another list called 'path_sorted'.
                found = False
                for x in range(M):
                    if path_sorted[x].equals_functions[hierarchy_level-1](FU): 	# -- if FU in sorted path is same as FU in unsorted path...
                        found = True 							# 	..mark that FU as True!
                    #endif
                #endfor

                # -- make a copy of this functional unit so that we only have to change a few of its attributes:
                temp_FU = copy(FU)

                if found == True:
                    # -- swap for human step
                    temp_FU.setIndication("Human")
                    temp_FU.setSuccessRate(1.0)
                #endif

                temp_path.append(temp_FU)
            #endfor

            candidate_paths.append(temp_path)
        #endfor

        # -- print all success rates for each value of M :
        print('BEST PATH TREES FOR VALUES OF M:\n--------------------------------')
        max_SR = -1.0; index = 0; path_count = 0
        for C in candidate_paths:
            total_success_rate = 1.0

            # -- compute the total success rate of this path:
            for FU in C:
                total_success_rate = total_success_rate * FU.getSuccessRate() if FU.getSuccessRate() else -1.0
            #endfor

            print("M = " + str(M) + " : new success rate for path #" + str(path_count) + " -- " + str(total_success_rate))
            if max_SR < total_success_rate:
                max_SR = total_success_rate
                index = candidate_paths.index(C)
            #endif
            path_count += 1	# -- increment count before each path
        #endfor
        print('--------------------------------')

        _file = open(folder+"FOON_M=" + str(M) + "-path_#" + str(index + 1) + "_to-" + goalNode.getObjectKey(hierarchy_level) + "_lvl" + str(hierarchy_level) + ".txt", 'w')
        for FU in candidate_paths[index]:
            _file.write(FU.getInputsForFile())
            _file.write(FU.getMotionForFile())
            _file.write(FU.getOutputsForFile())
            _file.write("//\n")
        #endfor
        _file.close()

        optimal_paths.append ( candidate_paths[index] )
    #endfor

    return optimal_paths
#enddef

def _taskTreeRetrieval_optimal(goalType, goalState, hierarchy_level=3, environment=None):
    global verbose
    
    # -- sometimes we may define a specific kitchen; other times, we just stick to default:
    if not environment:
        file = input('  -- Please provide the name of the file with KITCHEN ITEMS (press ENTER ONLY to use default): > ')
        if file == '':
            environment = _loadKitchenList() # -- use default 'FOON-input_only_nodes.txt'
        else:
            environment = _loadKitchenList(file) # -- use a different text file with kitchen items
        #endif
    #endif

    # -- create a temporary goal node object which is used to find the exact target in FOON:
    goalNode = FOON.Object(objectID=int(goalType), objectLabel=None)
    for x in goalState:
        goalNode.addNewState([int(x), None, []])
    #endif

    if hierarchy_level == 1:
        searchNodes = FOON_nodes[0]
    elif hierarchy_level == 2:
        searchNodes = FOON_nodes[1]
    elif hierarchy_level == 3:
        searchNodes = FOON_nodes[2]
    else:
        return

    search_level = hierarchy_level
    if search_level == 3:
        search_level = 2	# -- we only consider level 2 nodes if we do not have exact candidate

    # -- we will identify different target goal nodes that have the same object/state combination:
    goals = []

    # NOTE: refer to the search_level description for a run-down of the intuiton here:
    index = -1
    for T in searchNodes:
        if isinstance(T, FOON.Object):
            if T.equals_lvl1(goalNode) and T.isSameStates_ID_only(goalNode):
                index = searchNodes.index(T)
                goals.append(searchNodes[index])

    if index == -1:
        print("Item " + goalNode.getObjectKey(hierarchy_level) + " has not been found in network!")
        return False
    #endif

    if verbose:
        print("\n-- Candidate goal nodes are as follows:")
        for G in goals:
            G.print_functions[hierarchy_level-1]()
    
    if verbose:
        print("\n-- Proceeding with task tree retrieval...\n")

    startNodes = []
    for T in environment:
        index = -1
        for N in searchNodes:
            if isinstance(N, FOON.Object):
                if T.equals_lvl1(N) and T.isSameStates_ID_only(N):
                    index = searchNodes.index(N)
                    break
        if index > -1:
            # -- this means that the object exists in FOON; if not..
            startNodes.append(searchNodes[index])
        else:
            try:
                import FOON_generalization as fgen
            except ImportError:
                pass
            else:	
                # .. we can try to find a substitute for this object:
                possible_substitutes = fgen._findObjectSubstitute(T)

                for P in possible_substitutes:
                    index = -1
                    for N in searchNodes:
                        if P.equals_functions[hierarchy_level-1](N):
                            index = searchNodes.index(N); break
                    #endfor

                    if index > -1:
                        # -- this means that the object exists in FOON; if not..
                        startNodes.append(searchNodes[index])
                    #endif
                #endfor
            #endif
        #endif
    #endfor

    # NOTE: this function will first identify the "best" path, which is based on the availability of objects:

    # -- first, find all paths that reach the provided goal:
    all_paths = _findAllPaths(goalType, goalState, hierarchy_level)
    best_path_count, best_path = 0, 0

    for T in all_paths:
        # -- note all objects required or referred to in the path tree T:
        objects_required = []
        for FU in T:
            for _input in FU.getInputList():
                if _input in objects_required:
                    continue
                objects_required.append(_input)
            for _output in FU.getOutputList():
                if _output in objects_required:
                    continue
                objects_required.append(_output)
        #endfor

        count = 0
        for O in objects_required:
            if O in startNodes:
                count += 1

        # -- keep note of the best path with most overlap:
        if best_path_count < count:
            best_path = all_paths.index(T); best_path_count = count
    #endfor

    # TODO: more tests..
    return all_paths[best_path]
#enddef

def _pathTreeRetrieval(goalType, goalState, hierarchy_level=3, skip_prompts=False):
    # -- first, identify all possible paths in the network:
    all_path_trees = _findAllPaths(goalType, goalState, hierarchy_level)
    all_path_trees.sort(key=len)

    if not skip_prompts:
        _response = input(' -- Print length of all paths? [Y/N] > ')
        if _response == 'y' or _response == 'Y':
            for path in all_path_trees:
                total_success_rate = 1.0
                for FU in path:
                    total_success_rate = total_success_rate * (FU.getSuccessRate() if FU.getSuccessRate() else -1.0)
                print("length of path #" + str(all_path_trees.index(path)) + "\t:\t" + str(len(path)) + ' - ' + (str(total_success_rate) if total_success_rate >= 0 else 'N/A %'))

    # -- then, let's only keep the upper X-% of shortest length paths, so we can discard nonsensical paths:
    #shortest_paths = all_path_trees[:int( 0.05 * len(all_path_trees)) + 1]

    # -- we can find the average length of a path and keep those that are below the average:
    avg_path_length = 0
    for x in all_path_trees:
        avg_path_length += len(x)
    avg_path_length /= len(all_path_trees)

    shortest_paths = [P for P in all_path_trees if len(P) < avg_path_length + 1]

    if not skip_prompts:
        _response = input('\n -- Save preliminary path trees to disk? [Y/N] (default : N) > ')
        if _response.lower() == 'y':
            # -- prompt user for whether to save all the paths or to only save the best X-% (if there are that many):
            _response = input('  -- Save ALL or BELOW AVG. LENGTH? [1/2] > (default : 1)')
            paths_to_print = all_path_trees
        
            if _response == '2':
                paths_to_print = shortest_paths
            #endif

            folder = "path_trees_to_O" + str(goalType) + "S" + str(goalState) + "/"
            if not os.path.exists(folder):
                os.makedirs(folder)

            for task_tree in tqdm.tqdm(paths_to_print):
                # -- produce all files to the different paths to verify that the M swapping is working correctly:

                path_count = paths_to_print.index(task_tree)

                # -- remember, we save as two file types now: 1) TXT file, and 2) JSON file.
                _file = open(folder + "FOON_path_#" + str(path_count) + "_to_O" + str(goalType) + "S" + str(goalState) + "_lvl" + str(hierarchy_level) + ".txt", 'w')
                for FU in task_tree:
                    _file.write(FU.getFunctionalUnitText())
                #endfor
                _file.close()

                try:
                    import json
                except ImportError:
                    pass
                else:
                    subgraph_units = {}
                    subgraph_units['functional_units'] = []

                    _file = open(folder + "FOON_path_#" + str(path_count) + "_to_O" + str(goalType) + "S" + str(goalState) + "_lvl" + str(hierarchy_level) + ".json", 'w')
                    for FU in task_tree:
                        subgraph_units['functional_units'].append(FU.getFunctionalUnitJSON())
                    json.dump(subgraph_units, _file, indent=7)
                    _file.close()
                #endtry
            #endfor
        #endif

    if not skip_prompts:
        # -- although we ask the user if we should print ALL or upper-X%, let's only work on the upper-X%:
        _response = input('\n -- Proceed with human-cobot task tree planning? [Y/N] (default: N) > ')
        if _response == 'Y' or _response == 'y':
            return _taskTreeRetrieval_weighted(shortest_paths, goalType, goalState, hierarchy_level)
    
    if not skip_prompts:
        return shortest_paths

    return all_path_trees
#enddef

def _findAllPaths_old(goalType, goalState, hierarchy_level=3):
    global FOON_functionalUnits, FOON_nodes, FOON_outputsToUnits

    # -- note the level we are searching at, selecting the right FOON: 
    goalNode = FOON.Object(objectID=int(goalType), objectLabel=None)
    for x in goalState:
        goalNode.addNewState([int(x), None, []])

    searchNodes = None; searchFOON = None; searchMap = None

    if hierarchy_level == 1 or hierarchy_level == 2 or hierarchy_level == 3:
        searchNodes = FOON_nodes[hierarchy_level-1]
        searchFOON = FOON_functionalUnits[hierarchy_level-1]
        searchMap = FOON_outputsToUnits[hierarchy_level-1]
    else:
        print(' -- ERROR: provided invalid hierarchy level as argument to function! Must be between 1 and 3 (inclusive).')
        return

    # -- first part: check if the object actually exists in the network:

    # NOTE: when searching for the procedure to make a single item, we need to negate the ingredients usage.
    #	-- when searching level 3, we default to level 2 to find all object/state combinations of a goal node: 
    search_level = hierarchy_level
    if search_level == 3:
        search_level = 2

    # -- list of ALL possible functional units that can be used for making the item:
    global verbose; all_path_trees = [] 

    print(' -- Searching for goal node candidates in FOON (level ' + str(hierarchy_level) + '...')

    goal_index = []
    for T in searchNodes:
        if isinstance(T, FOON.Object):
            if T.equals_lvl1(goalNode) and T.isSameStates_ID_only(goalNode):
                goal_index.append( searchNodes.index(T) )
                print('  -- Added goal node:')
                T.print_functions[hierarchy_level-1]()

    if not goal_index:
        print(" -- Item " + str(goalNode.getObjectKey(hierarchy_level)) + " has not been found in network!")
        return all_path_trees
    #endif

    # NOTE: Necessary lists needed to keep track of the tree we are creating.
    #	-- 'tree_stack' is used for creating new children using combination of FUs that make the parent node's input nodes (see below)
    # 	-- 'root_nodes' contains the original root nodes for the trees we are growing.
    root_nodes = collections.deque()

    # -- map the goal node to its respective root node:
    goal_to_root = {}

    # STEP 1: Find all root nodes (i.e. all FUs that make the original goal node) to different trees for each goal node:
    for G in goal_index:
        # -- this is the actual goal node which is in the network:
        goalNode = searchNodes[G]	

        for FU in searchFOON:
            # -- searching for all functional units with our goal as output
            for N in FU.getOutputList():
                if N.equals_functions[search_level-1](goalNode):				
                    # -- create roots for path trees:
                    node = FOON.TreeNode()
                    node.setUnitsToTreeNode( [searchFOON.index(FU)] )
                    root_nodes.append(node)

                    # -- note mapping of the root to its intended goal node:
                    goal_to_root[node] = goalNode
                #endif
            #endfor
        #endfor
    #endfor

    for _root in root_nodes:
        start_time = time.time()

        print('\n  -- Starting root #' + str(root_nodes.index(_root)) + '...')
        
        # -- initialize the tree stack here for each root node:
        tree_stack = collections.deque(); tree_stack.append(_root)

        # -- create a set that enforces uniqueness of certain tree nodes (based on contained units):
        tree_set = {}

        # NOTE: we can possibly have many object nodes that are suitable as the goal node;
        #	we will go through each of these candidate targets:
        goalNode = goal_to_root[_root]

        # NOTE: relevant ingredients are ingredients that pertain to the creation of the goal node:
        relevant_ingredients = goalNode.getIngredients() if goalNode.hasIngredients() else []
        for _input in searchFOON[_root.getUnitsInTreeNode()[0]].getInputNodes():
            if _input.hasIngredients():
                relevant_ingredients = list(set(relevant_ingredients) | set(_input.getIngredients()))

        # -- keep track of items that have already been seen using this set:
        items_seen = set()

        # Step 2: Create a tree of functional units that can be used for exploring all possible paths with DFS:
        while tree_stack:

            head = tree_stack.popleft()

            if verbose:
                print("tree node:")
                print(" -children : " + str(head.getChildren()) )
                print(" -contained : " + str((head.getUnitsInTreeNode())) )
        
            if verbose:	
                for FU in head.getUnitsInTreeNode():
                    print( str(searchFOON.index(FU)) )

            permutations = set()

            # # -- keep track of items that have already been seen using this set:
            items_seen = head.getItemsSeen()

            # -- pre-build ancestors list such that each TreeNode contains it for quick and easy reference:
            ancestors = set(head.getUnitsInTreeNode()) | set(head.getAncestors())

            # -- search for all functional units that create the COMBINATION of input nodes in the root:
            for _FU in head.getUnitsInTreeNode():
                for _input in searchFOON[_FU].getInputList():

                    temp_object_id = searchNodes.index(_input)
                    if temp_object_id in items_seen:
                        continue

                    items_seen.add(temp_object_id)

                    # -- for all inputs for the root FU node..
                    try:					
                        candidates = [searchFOON.index(I) for I in searchMap[_input]]
                    except KeyError:
                        continue			

                    # -- making sure we only explore functional units relevant to the goal:
                    if relevant_ingredients:
                        # _input.print_functions[hierarchy_level-1]()

                        # -- make a temporary list containing units deemed relevant:
                        revised_candidates = []
                        for C in candidates:
                            # -- identify all ingredients used by outputs for each candidate:
                            ingredients_required = []
                            for _output in searchFOON[C].getOutputNodes():
                                for I in _output.getIngredients():
                                    ingredients_required.append(I)
                                #endif
                            #endif

                            # -- make sure we only have unique instances of ingredients:
                            ingredients_required = list(set(ingredients_required))
                            num_ingredients_required = len(ingredients_required)
                            num_ingredients_left = len(list(set(ingredients_required) - set(relevant_ingredients)))

                            # print(relevant_ingredients)
                            # print(ingredients_required)

                            if not ingredients_required:
                                revised_candidates.append(C)
                            elif num_ingredients_left / num_ingredients_required <= 0.25 and num_ingredients_left < num_ingredients_required:
                                revised_candidates.append(C)

                                #relevant_ingredients = list(set(relevant_ingredients) | set(ingredients_required))
                                # print('yes')
                                # searchFOON[C].print_functions[hierarchy_level-1]()
                            else:
                                # print('no')
                                ancestors.add(C)
                                pass
                            # input()
                        #endfor

                        candidates = revised_candidates
                    #endif
    
                    temp_list = frozenset( set(candidates) - ancestors )

                    if verbose:
                        input()
                        print(' -- current list of unseen functional units: ' + str(temp_list))
        
                    if temp_list:
                        permutations.add(temp_list)

                    # #endfor 				
                #endfor
            #endfor

            # -- remove all empty sets that cause incorrect calculations!
            # -- this happens when we come across a 'leaf' FU with NO functional units that create the inputs for this tree node.
            permutations = list(filter(None, permutations))
            if not permutations:
                continue

            # --  we use a set() to keep UNIQUE copies of children:
            new_children = set()
            
            # -- NOTE: itertools.product() is a function that is used for calculating all sets 
            # 	(the number of ways of selecting items in order) of a given set of items.
            # -- For example: given the sets [1, 2] and [2, 3], the total number of Cartesian sets would be:
            #		[1, 2], [1, 3], [2, 2], [2, 3]
            for P in IT.product(*permutations):
                # Interesting note: set((1,2)) == set((2,1)) will be True, so this is why we don't have to worry!

                # -- add the tuples to the set, as it will only keep unique Cartesian sets:
                new_children.add(frozenset(P))
            #endfor

            new_children = list(new_children)
            # -- pruning certain sets:
            # new_children.sort(key=len)
            # new_children = set(new_children[:int( 0.01 * len(new_children)) + 1])

            for C in new_children:
                # -- flag reflecting if tree node has been explored before (i.e. it has been created) or not:
                is_new_node = False

                # NOTE: C will be a frozen set object, making it immutable:
                if C not in tree_set:
                    tree_set[C] = FOON.TreeNode()
                    is_new_node = True
                # else:
                    # print('this combination already explored')
                #end

                # -- with this child, we need to set its attributes and parents accordingly:
                child = tree_set[C]

                # child = FOON.TreeNode(); is_new_node = True
                
                # -- get the units already contained in this tree node (if any exist) 
                # 	and merge them with the new set C:
                child.setUnitsToTreeNode( list(set(child.getUnitsInTreeNode()) | C) )
                child.setItemsSeen( child.getItemsSeen() | items_seen )
    
                # -- merge child's ancestors (if any) with ancestors from its parent:
                child.setAncestors( ancestors | child.getAncestors() )

                # -- set parents and children here; check if we won't be making duplicates here:
                head.addChild(child)

                child.addParent(head)

                # -- only change this child's level if it did not exist before (i.e. has default value of 0):
                if child.getLevel() == 0:
                    child.setLevel(int(head.getLevel()) + 1)

                if verbose:
                    child.printTreeNode(searchFOON)
                #endif

                if is_new_node:
                    # -- add new TreeNode to the deque if we just added a completely new tree node:				
                    tree_stack.appendleft(child)
            
            #endfor

            if verbose:
                input("Press ENTER to continue...")

        #endwhile

        end_time = time.time()
    
        print('   -- Time taken to explore root #' + str(root_nodes.index(_root)) + ' : ' + (str(end_time - start_time)) + ' s..')
        print('   -- Total objects seen in exploration : ' + str(len(items_seen)) + " / " + str(len(searchMap)))

    #endfor

    if verbose:
        print('\n -- printing entire path tree:\n')
        for R in root_nodes:
            FOON.TreeNode.printPathTree(R)
            print()

    # Step 3: Save all paths from all possible root nodes as found in Step 1 to a list.
    for R in root_nodes:
        for path in FOON.TreeNode.makeList(R):
            path.reverse()	# -- everything will be saved as reverse order, so switch it around.
            
            # -- save all task trees found by algorithm to this list:	
            task_tree = [searchFOON[FU] for FU in path]
            print(len(task_tree))
            all_path_trees.append(task_tree)
        #endfor
    #endfor

    print('\n  -- Total number of task trees found : ' + str(len(all_path_trees)) + '\n')

    return all_path_trees
#enddef

def _findAllPaths_2(goalType, goalState, hierarchy_level=3):
    global FOON_functionalUnits, FOON_nodes, FOON_outputsToUnits

    # -- note the level we are searching at, selecting the right FOON: 
    goalNode = FOON.Object(objectID=int(goalType), objectLabel=None)
    for x in goalState:
        goalNode.addNewState([int(x), None, []])

    searchNodes = None; searchFOON = None; searchMap = None

    if hierarchy_level == 1 or hierarchy_level == 2 or hierarchy_level == 3:
        searchNodes = FOON_nodes[hierarchy_level-1]
        searchFOON = FOON_functionalUnits[hierarchy_level-1]
        searchMap = FOON_outputsToUnits[hierarchy_level-1]
    else:
        print(' -- ERROR: provided invalid hierarchy level as argument to function! Must be between 1 and 3 (inclusive).')
        return

    # -- first part: check if the object actually exists in the network:

    # NOTE: when searching for the procedure to make a single item, we need to negate the ingredients usage.
    #	-- when searching level 3, we default to level 2 to find all object/state combinations of a goal node: 
    search_level = hierarchy_level
    if search_level == 3:
        search_level = 2

    # -- list of ALL possible functional units that can be used for making the item:
    global verbose; all_path_trees = [] 

    index = -1
    for T in searchNodes:
        if isinstance(T, FOON.Object):
            if T.equals_lvl1(goalNode) and T.isSameStates_ID_only(goalNode):
                index = searchNodes.index(T)
                print('-- Added goal node:')
                T.print_functions[hierarchy_level-1]()

    if index == -1:
        print("Item " + str(goalNode.getObjectKey(hierarchy_level)) + " has not been found in network!")
        return all_path_trees
    #endif

    # NOTE: Necessary lists needed to keep track of the tree we are creating.
    #	-- 'tree_stack' is used for creating new children using combination of FUs that make the parent node's input nodes (see below)
    # 	-- 'root_nodes' contains the original root nodes for the trees we are growing.
    root_nodes = collections.deque()

    # -- this is the actual goal node which is in the network:
    goalNode = searchNodes[index]	
    
    # Step 1: Find all root nodes (i.e. all FUs that make the original goal node) to different trees:
    for FU in searchFOON:
        # -- searching for all functional units with our goal as output
        for N in FU.getOutputList():
            if N.equals_functions[search_level-1](goalNode):
                root_nodes.append(searchFOON.index(FU))
        #endfor
    #endfor

    solutions = []

    for _root in root_nodes:
        start_time = time.time()

        print('\n  -- Starting root #' + str(root_nodes.index(_root)) + '...')
        
        # -- initialize the tree stack here for each root node:
        tree_stack = collections.deque(); tree_stack.append(_root)

        # -- keep a list of all preliminary paths that we modify and build throughout the search:
        paths = collections.deque(); paths.append([_root])

        # -- keep track of all items that have been evaluated for each path in the works:
        items_seen = {}; items_seen[0] = set({index})

        while tree_stack:
            print(len(tree_stack))
            head = tree_stack.popleft()

            permutations = set()

            inputs_evaluated = list()

            for _input in searchFOON[head].getInputList():
                # -- for all inputs for the root FU node..
                candidates = None
                try:					
                    candidates = [searchFOON.index(I) for I in searchMap[_input]]
                except KeyError:
                    pass
                #endtry
    
                if candidates:
                    temp_list = frozenset(candidates)
                    inputs_evaluated.append(searchNodes.index(_input))
                    permutations.add(temp_list)

            if not permutations:
                continue
            
            new_children = set()
            for P in IT.product(*permutations):
                # Interesting note: set((1,2)) == set((2,1)) will be True, so this is why we don't have to worry!

                # -- add the tuples to the set, as it will only keep unique Cartesian sets:
                new_children.add(frozenset(P))
            #endfor

            # -- convert set of sets into list of lists for ease of use:
            new_children = [list(S) for S in new_children]

            # -- we will be making duplicates of existing paths (if they are relevant to this present head)
            #	and add them to new_paths temporarily.
            new_paths = []; new_items_seen = {}

            changes = False		

            candidates_for_stack = set()

            print(len(paths))

            for old_path in paths:
                
                if head in old_path:
                    # -- this means that a certain path has some relation to the head we are currently on:
    
                    for _set in new_children:
                        # --  a set is one of the computed Cartesian products from above:

                        # -- we take the record of what items have already been solved for a particular path:
                        temp_path = list(old_path)
                        temp_items_seen = items_seen[paths.index(old_path)].copy()

                        # -- we need to gatekeep to make sure that we are not exploring something we have already solved:
                        for y in range(len(_set)):
                            # -- for each item in the Cartesian product...

                            if inputs_evaluated[y] in temp_items_seen or _set[y] in temp_path:
                                # ... check if the object for the candidate unit already was solved:
                                # -- if the input object has already been seen, then no need to try and add a functional unit 
                                # 	to the path that solves it again:	
                                pass
                            else:
                                # searchNodes[inputs_evaluated[y]].print_functions[hierarchy_level-1]()
                                # -- we note if changes were made such that we will 
                                # 	override the old paths list with new one:
                                changes = True


                                # -- append changes to the path and items seen lists:
                                temp_path.append(_set[y])
                                temp_items_seen.add(inputs_evaluated[y])

                                candidates_for_stack.add(_set[y])
                                # tree_stack.append(_set[y])
                            #endif
                        #endfor
                        
                        print(temp_path)
                        print(temp_items_seen)

                        new_paths.append(temp_path)
                        new_items_seen[len(new_paths)-1] = temp_items_seen
                    #endfor
                else:
                    new_paths.append(old_path)
                    new_items_seen[len(new_paths)-1] = items_seen[paths.index(old_path)]

                #endif 

            #endfor

            input(len(new_paths) == len(new_items_seen))

            if changes:
                # -- we override the list of paths with the new set as well as the items seen for each path:			
                paths = new_paths
                print(len(paths))
                paths = set([frozenset(x) for x in paths])
                paths = [list(x) for x in paths]
                print(len(paths))

                print(len(paths))
                items_seen = new_items_seen

                # -- we only add certain elements to the tree stack if we need to further explore 
                # 	(i.e. we added new things to paths)
                for C in candidates_for_stack:
                    tree_stack.append(C)

        paths = set([frozenset(x.sort()) for x in paths])
        paths = [list(x) for x in paths]

        for P in paths:
            print(P)
            solutions.append(P)

        print(len(solutions))

        end_time = time.time()
    
        print('   -- Time taken to explore root #' + str(root_nodes.index(_root)) + ' : ' + (str(end_time - start_time)) + ' s..')

    for S in solutions:
        S.reverse()	# -- everything will be saved as reverse order, so switch it around.
        
        # -- save all task trees found by algorithm to this list:	
        task_tree = [searchFOON[FU] for FU in S]
        all_path_trees.append(task_tree)

    return all_path_trees
#enddef

def _findAllPaths(goalType, goalState, hierarchy_level=3, check_ingredients=True, max_height=sys.maxsize, max_children=sys.maxsize, end_early=False, objects_to_keep=[]):
    '''
    Finds all path trees to make a given goal, which is an object in FOON.

    Parameters:
        goalType (int): An integer referring to the goal object's ID
        goalState (list): An list of integers referring to the goal object's state ID(s)
        hierarchy_level (int): The hierarchy level to be considered when searching (default: 3)
        check_ingredients (bool): Flag to determine whether to check for ingredient context for searching (default: True)
        max_height (int): The maximum allowed height that a path tree node can have; a restrained path tree will be faster to build, but it may not be complete (default: sys.maxsize)
        max_children (int): The maximum allowed children that a path tree node can have; the smaller, the better, but less likely to get good results (default: sys.maxsize)
        downsize (bool) : Flag to end search when a single path has ended (i.e., a tree node has no children) (default: False)
        objects_to_keep (list) : List of object labels to keep when propagating path tree; anything not in this list is removed from functional units.

    Returns:
        all_path_trees (list): A list of all path trees found; if goal node is not found in FOON, it will be empty.
    '''

    # NOTE: this is a greedy version of the path tree retrieval; what makes it greedy is that we set a limit to the
    #	number of children created by each node of the tree, which is reflected by the variable 'max_children'.

    print('\n -- [PATH_TREE] : Commencing path tree retrieval with the following parameters:')
    print('    -> hierarchy_level = ' + str(hierarchy_level))
    if check_ingredients:
        print('    -> checking for ingredient context? = YES')
    else:
        print('    -> checking for ingredient context? = NO')
    if max_children < sys.maxsize:
        print('    -> maximum children allowed = ' + str(max_children))
    if objects_to_keep:
        print('    -> performing task tree generation pruning? = YES')

    global FOON_functionalUnits, FOON_nodes, FOON_outputsToUnits, verbose

    # NOTE: Three major steps to this algorithm:
    #	1. Identify all possible root nodes (roots are the functional units that IMMEDIATELY produce the given goal);
    #	2. Build and propagate a path tree that starts from each root that fulfills requirements to make the goal;
    #	3. Explore all roots using DFS to acquire each unique path that create the goal node.

    # -- note the level we are searching at, selecting the right FOON: 
    goalNode = FOON.Object(objectID=int(goalType), objectLabel=None)
    for x in goalState:
        goalNode.addNewState([int(x), None, []])

    # -- assign the right FOON structures to these variables:
    searchNodes = None; searchFOON = None; searchMap = None
    if hierarchy_level == 1 or hierarchy_level == 2 or hierarchy_level == 3:
        searchNodes = FOON_nodes[hierarchy_level-1]
        searchFOON = FOON_functionalUnits[hierarchy_level-1]
        searchMap = FOON_outputsToUnits[hierarchy_level-1]
    else:
        print(' -- ERROR: provided invalid hierarchy level as argument to function! Must be between 1 and 3 (inclusive).')
        return
    #endif

    # NOTE: when searching for the procedure to make a single item, we need to negate the ingredients usage.
    #	-- when searching level 3, we default to level 2 to find all object/state combinations of a goal node: 
    search_level = hierarchy_level
    if search_level == 3:
        search_level = 2

    # -- list of ALL possible functional units that can be used for making the item:
    all_path_trees = []

    print('\n -- [PATH_TREE] : Searching for goal node candidates in FOON (level ' + str(hierarchy_level) + ')...')

    # -- first part: check if the object actually exists in the network:
    goal_index = []
    for T in searchNodes:
        if isinstance(T, FOON.Object):
            if T.equals_lvl1(goalNode) and T.isSameStates_ID_only(goalNode):
                goal_index.append( searchNodes.index(T) )
                print('  -- Goal node # ' + str(len(goal_index)) + ':')
                T.print_functions[hierarchy_level-1]()
                print()
            #endif
        #endif
    #endfor

    if not goal_index:
        print(" -- Item " + str(goalNode.getObjectKey(hierarchy_level)) + " has not been found in network!")
        return all_path_trees
    #endif

    # NOTE: Necessary lists needed to keep track of the tree we are creating.
    #	-- 'tree_stack' is used for creating new children using combination of FUs that make the parent node's input nodes (see below)
    # 	-- 'root_nodes' contains the original root nodes for the trees we are growing.
    root_nodes = collections.deque()

    # -- map the goal node to its respective root node:
    goal_to_root = {}


    # NOTE: if we are using this for task tree generation, then we may want to do something different..
    #	this means that we would want to do some preliminary pruning of objects and branches that are not necessary.
    # -- in the regular path tree retrieval, to be more memory-efficient, we only consider the functional unit's by their 
    # 	index values when storing units within path tree nodes
    # -- in this case, we will use a dictionary that maps pruned units to their original unit index such that we do not
    # 	need to modify this function greatly:
    mapping_to_pruned_units = {}

    # STEP 1: Find all root nodes (i.e. all FUs that make the original goal node) to different trees for each goal node:
    for G in goal_index:
        # -- this is the actual goal node which is in the network:
        goalNode = searchNodes[G]	

        for FU in searchFOON:
            # -- searching for all functional units with our goal as output
            for N in FU.getOutputList():
                if N.equals_functions[search_level-1](goalNode):				
                    # -- create roots for path trees:
                    node = FOON.TreeNode()
                    node.setUnitsToTreeNode( [searchFOON.index(FU)] )
                    root_nodes.append(node)

                    # -- note mapping of the root to its intended goal node:
                    goal_to_root[node] = goalNode

                    # NOTE: functional unit pruning:
                    if objects_to_keep:
                        # -- we will use a mapping between the functional unit to a pruned unit:
                        temp_FU, count = FOON.FunctionalUnit(), 0
                        temp_FU.setMotionNode(FOON.Motion(motionID=FU.getMotion().getMotionType(), motionLabel=FU.getMotion().getMotionLabel()))

                        # -- main idea here: remove any input nodes in all functional units that are not relevant to what we need:
                        for _input in FU.getInputNodes():
                            if _input.getObjectLabel() in objects_to_keep:
                                temp_FU.addObjectNode( _input, True, FU.getMotionDescriptor(count, is_input=True) )					
                            #endif
                            count += 1
                        #endfor

                        count = 0
                        for _output in FU.getOutputNodes():
                            if _output.getObjectLabel() in objects_to_keep:
                                temp_FU.addObjectNode( _output, False, FU.getMotionDescriptor(count, is_input=False) )					
                            #endif
                            count += 1
                        #endfor

                        if searchFOON.index(FU) not in mapping_to_pruned_units:
                            mapping_to_pruned_units[searchFOON.index(FU)] = temp_FU
                        #endif
                    #endif
                    # NOTE: end of functional unit pruning part.

                #endif
            #endfor
        #endfor
    #endfor

    print(' -- [PATH_TREE] : Beginning search...')

    response = input('  -- Which object would you like to set as target? (Press ENTER for no preference) > ')
    if response:
        root_nodes = collections.deque( [root_nodes[int(response)-1]] )

    for _root in root_nodes:
        start_time = time.time()

        print('  -- Starting root #' + str(root_nodes.index(_root)) + '...')
        
        # -- initialize the tree stack here for each root node:
        tree_stack = collections.deque(); tree_stack.append(_root)

        # -- create a set that enforces uniqueness of certain tree nodes (based on contained units):
        tree_set = {}

        # NOTE: we can possibly have many object nodes that are suitable as the goal node;
        #	we will go through each of these candidate targets:
        goalNode = goal_to_root[_root]

        # -- keep track of items that have already been seen using this set:
        items_seen = set()

        # NOTE: relevant ingredients are ingredients that pertain to the creation of the goal node:
        relevant_ingredients = goalNode.getIngredients() if goalNode.hasIngredients() else []

        for _unit in _root.getUnitsInTreeNode(): # there should only be one, but just writing it in this way.
            if not objects_to_keep:
                # NOTE: here, we are just performing regular path tree retrieval (NO PRUNING).

                # -- we check the inputs of the functional unit to see if any different ingredients are being used:
                for _input in searchFOON[_unit].getInputNodes():
                    if _input.hasIngredients():
                        relevant_ingredients = list(set(relevant_ingredients) | set(_input.getIngredients()))
                    #endif
                #endfor

                # -- we can also immediately mark off the outputs for this root's functional unit as being seen, 
                #	since this functional unit will already be "executed":
                for _output in searchFOON[_unit].getOutputNodes():
                    # -- get the object's index and add to list of items seen:
                    temp_object_id = searchNodes.index(_output)
                    items_seen.add( temp_object_id )
                #endfor

            else:
                # NOTE: here, we are just pruning while performing path tree retrieval:

                for _input in mapping_to_pruned_units[_unit].getInputNodes():
                    if _input.hasIngredients():
                        relevant_ingredients = list(set(relevant_ingredients) | set(_input.getIngredients()))
                    #endif
                #endfor

                for _output in mapping_to_pruned_units[_unit].getOutputNodes():
                    # -- get the object's index and add to list of items seen:
                    temp_object_id = searchNodes.index(_output)
                    items_seen.add( temp_object_id )
                #endfor

            #endif
        #endfor

        # Step 2: Create a tree of functional units that can be used for exploring all possible paths with DFS:
        while tree_stack:

            # NOTE: pop left from deque -> FIFO -> breadth-first ordering!
            #head = tree_stack.pop()
            head = tree_stack.popleft()

            # -- check if the popped tree node exceeds our given path tree height/depth limit:
            if head.getLevel() > max_height:
                continue

            if verbose:
                print("tree node:")
                print(" -children : " + str(head.getChildren()) )
                print(" -contained : " + str((head.getUnitsInTreeNode())) )
        
            if verbose:	
                for FU in head.getUnitsInTreeNode():
                    print( str(searchFOON.index(FU)) )

            # NOTE: permutations 
            permutations = set()

            # # -- keep track of items that have already been seen using this set:
            items_seen = head.getItemsSeen()

            # -- pre-build ancestors list such that each TreeNode contains it for quick and easy reference:
            ancestors = set(head.getUnitsInTreeNode()) | set(head.getAncestors())

            # -- search for all functional units that create the COMBINATION of input nodes in the root:
            for _FU in head.getUnitsInTreeNode():

                precondition_unit = mapping_to_pruned_units[_FU] if objects_to_keep else searchFOON[_FU]

                for _input in precondition_unit.getInputList():

                    # -- check if this node is considered to be a starting node:
                    if _isStartingNode(_input) or _isBaseState(_input):
                        if verbose:
                            _input.print_functions[2]()
                        continue

                    # -- check if we have already seen or explored this object before:
                    temp_object_id = searchNodes.index(_input)
                    if temp_object_id in items_seen:
                        continue

                    items_seen.add(temp_object_id)

                    # -- for all inputs for the root FU node..
                    try:					
                        candidates = [searchFOON.index(I) for I in searchMap[_input]]
                    except KeyError:
                        continue

                    # -- making sure we only explore functional units relevant to the goal:
                    if relevant_ingredients and check_ingredients:
                        # _input.print_functions[hierarchy_level-1]()

                        # -- make a temporary list containing units deemed relevant:
                        revised_candidates = []
                        for C in candidates:
                            # -- identify all ingredients used by outputs for each candidate:
                            ingredients_required = []
                            for _output in searchFOON[C].getOutputNodes():
                                # -- we check all output nodes in the candidate functional unit C and we take note of their ingredients:
                                for I in _output.getIngredients():
                                    ingredients_required.append(I)
                                #endif
                            #endif

                            # -- make sure we only have unique instances of ingredients:
                            ingredients_required = list(set(ingredients_required))
                            num_ingredients_required = len(ingredients_required)

                            # -- ingredients left - ingredients in the required set that have not been matched to the relevant ingredients for goal:
                            num_ingredients_left = len(list(set(ingredients_required) - set(relevant_ingredients)))

                            # -- for debugging purposes:
                            #print(ingredients_required)
                            #print(relevant_ingredients)
                            #input((set(ingredients_required) - set(relevant_ingredients)))

                            if not ingredients_required:
                                # -- if there are no ingredients required at all, then we don't have any context to worry about:
                                revised_candidates.append(C)

                            elif num_ingredients_left / num_ingredients_required <= 0.2 and num_ingredients_left < num_ingredients_required:
                                # -- this means that there was some overlap between C's required ingredients and the goal-relevant ingredients;
                                #	we can either base this relevance on some threshold (here, it is suggests that we must cover 75% of relevant ingredients) #
                                #	or we look for an exact match (which may not always be ideal)
                                revised_candidates.append(C)

                                # -- not sure if it's a good idea to combine the non-overlapping ingredients with the goal-relevant ingredients:
                                #relevant_ingredients = list(set(relevant_ingredients) | set(ingredients_required))

                            else:
                                # -- this means we did not meet the required overlap threshold; however, we should still treat it as if we visited this functional unit.
                                ancestors.add(C)

                            #endif
                        #endfor

                        # -- now that we evaluated the candidates for contextual relevance, let's now work with this new set:
                        candidates = revised_candidates
                    #endif
    
                    # -- just as a safety measure, let's make sure that there are no ancestor units (i.e. already visited units) in our candidate set:
                    final_candidates = frozenset( set(candidates) - ancestors )

                    # NOTE: functional unit pruning:
                    if objects_to_keep:
                        for C in final_candidates:
                            # -- we will use a mapping between the functional unit to a pruned unit:
                            temp_FU, count = FOON.FunctionalUnit(), 0

                            # -- first, set a motion node that is the same as the original functional unit's motion node:
                            temp_FU.setMotionNode(FOON.Motion(motionID=searchFOON[C].getMotion().getMotionType(), motionLabel=searchFOON[C].getMotion().getMotionLabel()))
                            
                            # -- main idea here: remove any input or output nodes in all functional units that are not relevant to what we need:

                            # NOTE: check input nodes for this candidate functional unit for any objects for pruning:
                            for _input in searchFOON[C].getInputNodes():
                                if _input.getObjectLabel() in objects_to_keep:
                                    # -- remove the input node that should have been pruned:
                                    temp_FU.addObjectNode( _input, True, searchFOON[C].getMotionDescriptor(count, is_input=True) )					
                                elif _input.hasIngredients():
                                    # -- remove any ingredients from the input node that should have been pruned:
                                    ingredients = list(set(objects_to_keep) | set(_input.getIngredients()))
                                    if len(ingredients) > 0:
                                        _input.setIngredients(ingredients)
                                        temp_FU.addObjectNode(  _input, True, FU.getMotionDescriptor(count, is_input=True) )
                                #endif
                                count += 1
                            #endfor

                            # NOTE: check output nodes for this candidate functional unit for any objects for pruning:
                            count = 0
                            for _output in searchFOON[C].getOutputNodes():
                                if _output.getObjectLabel() in objects_to_keep:
                                    # -- remove the output node that should have been pruned:
                                    temp_FU.addObjectNode( _output, False, searchFOON[C].getMotionDescriptor(count, is_input=False) )					
                                elif _output.hasIngredients():
                                    # -- remove any ingredients from the output node that should have been pruned:
                                    ingredients = list(set(objects_to_keep) | set(_input.getIngredients()))
                                    if len(ingredients) > 0:
                                        _output.setIngredients(ingredients)
                                        temp_FU.addObjectNode(  _output, False, FU.getMotionDescriptor(count, is_input=False) )
                                #endif								
                                count += 1
                            #endfor

                            if C not in mapping_to_pruned_units:
                                mapping_to_pruned_units[C] = temp_FU
                        #endfor
                    #endif

                    if verbose:
                        input()
                        print(' -- current list of unseen functional units: ' + str(final_candidates))
        
                    # -- only add the final candidate list if it is not empty:
                    if final_candidates: permutations.add(final_candidates)

                    #endfor 				
                #endfor
            #endfor

            # NOTE: we must remove all empty sets that cause incorrect calculations!
            # -- this happens when we come across a 'leaf' FU with NO functional units 
            # 	that create the inputs for this tree node.
            permutations = list(filter(None, permutations))
            if not permutations:
                # -- if we have an empty list, then that means that we hit a leaf node.
                if end_early: break
                continue

            # --  we use a set() to keep UNIQUE copies of children:
            new_children = set()
            
            # -- NOTE: itertools.product() is a function that is used for calculating all sets 
            # 	(the number of ways of selecting items in order) of a given set of items.
            # -- For example: given the sets [1, 2] and [2, 3], the total number of Cartesian sets would be:
            #		[1, 2], [1, 3], [2, 2], [2, 3]
            for P in IT.product(*permutations):
                # Interesting note: set((1,2)) == set((2,1)) will be True, so this is why we don't have to worry!

                # -- add the tuples to the set, as it will only keep unique Cartesian sets:
                new_children.add(frozenset(P))
            #endfor

            new_children = list(set(new_children))
            
            # -- we can sort the children from smallest to largest - the length will determine how many units are needed to fulfill head's requirements:
            new_children.sort(key=len)

            #input(new_children[0:10])

            # -- greedy version of the path tree search will only allow a certain number of children per tree node;
            #	we may not want to restrict it if we want optimal solutions:
            new_children = list(new_children[:min(max_children, len(new_children))])

            # -- once again trim more (in case of really large FOON):
            #new_children = new_children[:int(0.05 * len(new_children)) + 1]				

            for C in new_children:
                # -- flag reflecting if tree node has been explored before (i.e. it has been created) or not:
                is_new_node = False

                # NOTE: C will be a frozen set object, making it immutable:
                if C not in tree_set:
                    tree_set[C] = FOON.TreeNode()
                    is_new_node = True
                else:
                    if verbose: print('this combination already explored')
                #end

                # -- with this child, we need to set its attributes and parents accordingly:
                child = tree_set[C]
                
                # -- get the units already contained in this tree node (if any exist) 
                # 	and merge them with the new set C:
                child.setUnitsToTreeNode( list(set(child.getUnitsInTreeNode()) | C) )
    
                #if not is_new_node:
                #	print(C)
                #	print(child.getUnitsInTreeNode())
                #	print(list(set(child.getUnitsInTreeNode()) | C))
                #	input()
    
                # -- there may be some outputs to these functional units that have already been 
                #	seen or solved; maybe we should add them to the list of items seen:
                for unit in C:
                    for _output in searchFOON[unit].getOutputNodes():
                        # -- get the object's index and add to list of items seen:
                        temp_object_id = searchNodes.index(_output)
                        items_seen.add( temp_object_id )

                child.setItemsSeen( child.getItemsSeen() | items_seen )
    
                # -- merge child's ancestors (if any) with ancestors from its parent:
                child.setAncestors( ancestors | child.getAncestors() )

                # -- set parents and children here; check if we won't be making duplicates here:
                head.addChild(child); child.addParent(head)

                # -- only change this child's level if it did not exist before (i.e. has default value of 0):
                if child.getLevel() == 0:
                    child.setLevel(int(head.getLevel()) + 1)

                if verbose: child.printTreeNode(searchFOON)

                # -- add new TreeNode to the deque if we just added a completely new tree node:				
                if is_new_node: tree_stack.append(child)
                
            #endfor

            if verbose: input("Press ENTER to continue...")

        #endwhile

        end_time = time.time()
    
        print('   -- Time taken to explore root #' + str(root_nodes.index(_root)) + ' : ' + (str(end_time - start_time)) + ' s..')
        print('   -- Total objects seen in exploration : ' + str(len(items_seen)) + " / " + str(len(searchMap)) + '\n')

        if verbose:
            print(' -- [PATH_TREE] : Objects seen from exploring root #' + str(root_nodes.index(_root)) + ' are as follows:')
            for I in items_seen:
                searchNodes[I].print_functions[hierarchy_level-1]()
            #endfor
        #endif
    #endfor
    
    if verbose:
        print(' -- [PATH_TREE] : Printing trace of path trees:\n')
        for R in root_nodes:
            print('root #' + str(root_nodes.index(R)))
            FOON.TreeNode.printPathTree(R)
            print()

    # Step 3: Save all paths from all possible root nodes as found in Step 1 to a list.
    for R in root_nodes:
        for path in FOON.TreeNode.makeList(R):
            path.reverse()	# -- everything will be saved as reverse order, so switch it around.
            
            # -- save all task trees found by algorithm to this list:
            if not objects_to_keep:
                task_tree = [searchFOON[FU] for FU in path]
            else:
                # -- consider the pruned versions of functional units:
                task_tree = [mapping_to_pruned_units[FU].copyFunctionalUnit() for FU in path]
                
                # -- now, we need to remove the following:
                #	1. remove ALL instances of ingredient labels that are contained within remaining objects;
                #	2. remove all objects that have anything to do with irrelevant ingredients or objects.
                for FU in task_tree:
                    inputs_to_remove = []
                    for _input in FU.getInputNodes():
                        if not set(_input.getIngredients()) & set(objects_to_keep) and _input.getIngredients():
                            inputs_to_remove.append(_input)

                        ingredients_to_remove = []
                        for I in _input.getIngredients():
                            if I not in objects_to_keep:
                                ingredients_to_remove.append(I)

                        for I in ingredients_to_remove:
                            _input.objectIngredients.remove(I)

                    #endfor

                    for N in inputs_to_remove:
                        FU.inputNodes.remove(N)

                    outputs_to_remove = []
                    for _output in FU.getOutputNodes():
                        if not set(_output.getIngredients()) & set(objects_to_keep) and _output.getIngredients():
                            outputs_to_remove.append(_output)

                        ingredients_to_remove = []
                        for I in _output.getIngredients():
                            if I not in objects_to_keep:
                                ingredients_to_remove.append(I)

                        for I in ingredients_to_remove:
                            _output.objectIngredients.remove(I)

                    #endfor

                    for N in outputs_to_remove:
                        FU.outputNodes.remove(N)
                #endfor
            #endif

            all_path_trees.append(task_tree)

        #endfor
    #endfor

    print('\n -- [PATH_TREE]: Total number of task trees found : ' + str(len(all_path_trees)) + '\n')

    return all_path_trees
#enddef

###############################################################################################################################

def _start():

    def _printArgumentsUsage():
        print("ERROR: Unrecognized arguments given to script! Please use from one of the following:")
        print(" --help\t\t\t:- gives an overview of all the flags that work with the program")
        print(" --file='X.txt'\t\t:- open FOON file given as 'X.txt', where X can be any given name")
        print(" --verbose (or --v)\t:- this flag turns on verbose mode, which will result in MANY print-outs for debugging the program")
        print(" --goal_object=X\t\t:- this flag indicates the object type (for searching algorithms)")
        print(" --goal_state=[X, ...]\t:- this flag indicates the object's state(s) (for searching algorithms), provided as a list of numbers")
        print(" --algorithm=X\t\t:- this flag indicates whether to use path tree retrieval (X=PT) or regular task tree retrieval (X=TT) (default: TT)")
        print(" --search_level=[1/2/3]\t:- this indicates the level to use for the searching procedure (default: 3)")
    #enddef

    try:
        opts, _ = getopt.getopt( sys.argv[1:], 
                     'v:fi:ob:st:al:sl', 
                     ['verbose', 'file=', "goal_object=", "goal_state=", "algorithm=", "search_level=", 'help'] )	
    except getopt.GetoptError:
        _printArgumentsUsage(); exit()
    #end

    global verbose, goal_object_type, goal_state_type, search_level, retrieval_method

    retrieval_method = 1
    search_level = 3

    for opt, arg in opts:
        if opt in ('-v', '--verbose') or opt in ('-v', '--v'):
            print(" -- selected verbose option...")
            verbose = True

        elif opt in ('-fi', '--file'):
            file_name = arg

        # -- you can either define the search object or state here or in the program's arguments:
        elif opt in ('-ob', '--goal_object'):
            print(" -- given goal object type '" + str(arg) + "'")
            searchObject = arg

        elif opt in ('-st', '--goal_state'):
            print(" -- given goal object state '" + str(arg) + "'")
            searchState = ast.literal_eval(arg)

        elif opt in ('-al', '--algorithm'):
            if str(arg) == 'PT':
                retrieval_method = 2
            #endif

        elif opt in ('-sl', '--search_level'):
            print(" -- given hierarchy level to search: '" + str(arg) + "'")
            search_level = int(arg)

        else:
            _printArgumentsUsage(); exit()
        #end
    #endfor

    try:
        import FOON_graph_analyser as fga
    except ImportError:
        print(" -- ERROR: Missing FGA (FOON_graph_analyzer.py) file!")
        print("\t-- Download here: https://bitbucket.org/davidpaulius/foon_api/src/master/")
        exit()
    #end

    # -- check if config file is provided to the script:
    from configparser import ConfigParser

    config = None
    try:
        config_file = 'config.ini'
        config = ConfigParser()
        config.read_file(open(config_file))
    except FileNotFoundError:
        pass
    else:
        print(" -- Loaded configuration file 'config.ini' !")
    #end

    global last_updated; print("< frt: FOON_retrieval - (last updated " + str(last_updated) + " ) >")
    print( ("   --file:'" + str(file_name) + "'") if file_name else '')
    print("   --retrieval algorithm:'" + str('path tree')  if retrieval_method == 1 else 'greedy task tree')

    # -- use FGA to load the FOON subgraph file, build dictionaries for faster searching, and read index files for labels:
    fga._constructFOON(file_name)
    fga._buildInternalMaps()
    fga._readIndexFiles()

    _copyDicts({	
            'fu_list' : fga.FOON_functionalUnits, 
            'nodes_list' : fga.FOON_nodes, 
            'outputs_to_fu' : fga.FOON_outputsToUnits, 
            'objs_to_fu' : fga.FOON_objectsToUnits, 
            'fu_to_fu' : fga.FOON_functionalUnitMap,
            'labels' : fga.FOON_labels} 
        )

    _startRetrieval()
#enddef

if __name__ == '__main__':
    _start()