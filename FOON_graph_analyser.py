'''
FOON: Graph Analyzer (FOON_graph_analyzer):
-------------------------------------------
-- Written and maintained by: 
    * David Paulius (davidpaulius@usf.edu / dpaulius@cs.brown.edu)
    * Md Sadman Sakib (mdsadman@usf.edu)
-- Special thanks to undergraduates Kelvin Dong Sheng Pei and Sanjeeth Bhat.

NOTE: If using this program and/or annotations provided by our lab, please kindly cite our papers
    so that others may find our work:
* Paulius et al. 2016 - https://ieeexplore.ieee.org/abstract/document/7759413/
* Paulius et al. 2018 - https://ieeexplore.ieee.org/abstract/document/8460200/

'''

from __future__ import print_function
from builtins import input
import getopt, os, sys, time, ast

import tqdm

last_updated = '15th April, 2022'

# NOTE: you MUST have the accompanying 'FOON_classes.py'!
# -- you should probably find this file in the same repository as you found this script.
try:
    import FOON_classes as FOON
except ImportError:
    print(" -- ERROR: Missing 'FOON_classes.py' file! Make sure you have downloaded the accompanying class file!")
    print("\t-- Download here: https://bitbucket.org/davidpaulius/foon_api/src/master/")
    exit()
#end

# NOTE: Sadman recently introduced config files; here, we check config file for any flags (if one is present):
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

###############################################################################################################################

# NOTE: The following variables are typically referenced as global variables in inner functions or references:
FOON_node_count = 0	# -- total number of nodes (w.r.t level 3 of hierarchy):

# NOTE: list of all functional units for each hierarchy level:
#  -- hierarchy levels, FOON-EXP and FOON-GEN discussed in greater detail in Paulius et. al 2018
FOON_lvl1 = []; FOON_lvl2 = []; FOON_lvl3 = []

# NOTE: list of all nodes used for the functional unit lists above for each hierarchy level:
nodes_lvl1 = []; nodes_lvl2 = []; nodes_lvl3 = []

# NOTE: The following are dictionary structures used to map:
#  -- output objects to functional units:
FOON_outputsToUnits_lvl1 = {}; FOON_outputsToUnits_lvl2 = {}; FOON_outputsToUnits_lvl3 = {}
#  -- object to functional units (for both inputs or outputs):
FOON_objectsToUnits_lvl1 = {}; FOON_objectsToUnits_lvl2 = {}; FOON_objectsToUnits_lvl3 = {}
#  -- functional units to other units (determined by existence of overlapping input and output objects) :
FOON_functionalUnitMap_lvl1 = {}; FOON_functionalUnitMap_lvl2 = {}; FOON_functionalUnitMap_lvl3 = {}
#  -- motion nodes from the lists above to the functional units they are part of:
motionsToFunctionalUnits_lvl1 = {}; motionsToFunctionalUnits_lvl2 = {}; motionsToFunctionalUnits_lvl3 = {}

# NOTE: list collecting all of these lists and dictionaries:
FOON_functionalUnits = [FOON_lvl1, FOON_lvl2, FOON_lvl3]	# -- list of lists of functional units at all levels
FOON_nodes = [nodes_lvl1, nodes_lvl2, nodes_lvl3]		# -- list of lists of nodes at all levels
# -- list of all dictionaries mapping output objects to their respective functional units:
FOON_outputsToUnits = [FOON_outputsToUnits_lvl1, FOON_outputsToUnits_lvl2, FOON_outputsToUnits_lvl3]
# -- list of all dictionaries mapping ALL objects to their respective functional units:
FOON_objectsToUnits = [FOON_objectsToUnits_lvl1, FOON_objectsToUnits_lvl2, FOON_objectsToUnits_lvl3]
# -- list of all dictionaries mapping functional units to all other functional units with overlapping objects (inputs or outputs):
FOON_functionalUnitMap = [FOON_functionalUnitMap_lvl1, FOON_functionalUnitMap_lvl2, FOON_functionalUnitMap_lvl3]
# -- list of all dictionaries mapping motion nodes to their respective functional units:
motionsToFunctionalUnits = [motionsToFunctionalUnits_lvl1, motionsToFunctionalUnits_lvl2, motionsToFunctionalUnits_lvl3]

# NOTE: dictionary objects used for one-mode projection (graph of ONLY object nodes):
FOON_oneModeProjection_lvl1 = {}; FOON_oneModeProjection_lvl2 = {}; FOON_oneModeProjection_lvl3 = {}
# -- list of objects that are used in one-mode projection of object nodes:
objects_oneModeProjection_lvl1 = []; objects_oneModeProjection_lvl2 = []; objects_oneModeProjection_lvl3 = []

FOON_oneModeProjection = [FOON_oneModeProjection_lvl1, FOON_oneModeProjection_lvl2, FOON_oneModeProjection_lvl3]
objects_oneModeProjection = [objects_oneModeProjection_lvl1, objects_oneModeProjection_lvl2, objects_oneModeProjection_lvl3] 

# NOTE: dictionary mapping labels to IDs for objects, motions, and states:
FOON_objectLabels = {}; FOON_motionLabels = {}; FOON_stateLabels = {}
FOON_labels = {'objects' : FOON_objectLabels, 'motions' : FOON_motionLabels, 'states' : FOON_stateLabels}

# NOTE: storing the sense id for objects (based on WordNet) or to denote Concept-Net sense -- these were verified semi-automatically using parser!
FOON_objectSenses = {}

# NOTE: the following are dictionaries used for mapping categories to object labels (for generalization of FOON):
FOON_objectClasses = {} 

# NOTE: these lists are used for the generalization of FOON:
# -- Two "generalized" versions of FOON:
# 	1. FOON-EXP - expanded version of FOON that uses WordNet/Concept-Net similarities to create new units;
#		-- this would use the regular FOON lists from above since we perform expansion and read the new file created
# 	2. FOON-GEN - compressed version of FOON that uses object categories
# -- please refer to Paulius et al. 2018 for more explanation on these approaches.
FOON_GEN = []; nodes_GEN = []; FOON_object_map_GEN = {}
flag_EXP_complete = False
flag_GEN_complete = False

# NOTE: this dictionary is used to store the similarity value between pairs of objects:
object_similarity_index = {}

verbose = False	# -- change this if you would like more output to the console

# NOTE: name of the file name used for this FOON analyzer script:
file_name = None	# -- change this if you want to set default universal FOON file to FIXED file

# NOTE: flags used for _buildInternalMaps function:
flag_buildFunctionalUnitMap = False
flag_buildObjectToUnitMap = False
flag_mapsReady = False

FOON_video_source = []

# NOTE: global variable to store the location of the Concept-Net word embedding model (numberbatch);
#	you can download or find out more about this model here: https://github.com/commonsense/Concept-Net-numberbatch
#  -- override this with an actual path if you want to skip the prompts.
path_to_ConceptNet = None

# NOTE: version 2 means that we have performed functional unit chain compression into "combinational" functional units / hubs.
# -- see function *_findFunctionalUnitClusters* for more details
FOON_lvl1_ver2 = []; FOON_lvl2_ver2 = []; FOON_lvl3_ver2 = []
FOON_unitClusters = [FOON_lvl1_ver2, FOON_lvl2_ver2, FOON_lvl3_ver2]

###############################################################################################################################

# NOTE: loading of internal dictionaries that are used for the searching process:

def _buildInternalMaps():
    # NOTE: this function builds dictionary structures that will be used for the searching algorithms:
    print('\n -- [FOON-fga] : Building internal dictionaries...')

    global flag_buildFunctionalUnitMap, flag_buildObjectToUnitMap

    # -- make sure everything is cleared and then initialized:
    _resetMaps()

    # -- build mapping between output objects to the units that make them:
    _buildOutputsToUnitMap()
    
    # -- build mapping between functional units whose outputs overlap with another's inputs:
    if flag_buildFunctionalUnitMap:
        _buildFunctionalUnitMap()
    
    # -- building mapping between all objects and the functional units they appear in:
    if flag_buildObjectToUnitMap:
        _buildObjectToUnitMap()
#enddef

def _buildOutputsToUnitMap():
    # NOTE: create a mapping between all objects and related units based on outputs:
    print(' -- [FOON-fga] : Building output-to-FU dictionaries...')

    _buildOutputsToUnitMap_lvl1()
    print('  -- Level 1: Output object map complete!')
    _buildOutputsToUnitMap_lvl2()
    print('  -- Level 2: Output object map complete!')
    _buildOutputsToUnitMap_lvl3()
    print('  -- Level 3: Output object map complete!\n')
#enddef  	

def _buildOutputsToUnitMap_lvl1():
    global FOON_outputsToUnits_lvl1, nodes_lvl1, FOON_lvl1
    for _input in nodes_lvl1:
        if isinstance(_input, FOON.Object):
            procedures = []
            for _U in FOON_lvl1:
                for _output in _U.getOutputList():
                    if _input.equals_functions[0](_output):
                        procedures.append(_U); break
                    #endif	
                #endfor
            #endfor
            FOON_outputsToUnits_lvl1[_input] = procedures
        #endif
    #endfor
#enddef

def _buildOutputsToUnitMap_lvl2():
    global FOON_outputsToUnits_lvl2, nodes_lvl2, FOON_lvl2
    for _input in nodes_lvl2:
        if isinstance(_input, FOON.Object):
            procedures = []
            for _U in FOON_lvl2:
                for _output in _U.getOutputList():
                    if _input.equals_functions[1](_output):
                        procedures.append(_U); break
                    #endif	
                #endfor
            #endfor
            FOON_outputsToUnits_lvl2[_input] = procedures
        #endif
    #endfor
    return
#enddef

def _buildOutputsToUnitMap_lvl3():
    global FOON_outputsToUnits_lvl3, nodes_lvl3, FOON_lvl3
    for _input in nodes_lvl3:
        if isinstance(_input, FOON.Object):
            procedures = []
            for _U in FOON_lvl3:
                for _output in _U.getOutputList():
                    if _input.equals_functions[2](_output):
                        procedures.append(_U); break
                    #endif	
                #endfor
            #endfor
            FOON_outputsToUnits_lvl3[_input] = procedures
        #endif
    #endfor
    return
#enddef

def _buildObjectToUnitMap():
    # NOTE: create a mapping between all objects and related units:
    print(' -- [FOON-fga] : Building object-to-FU dictionaries...')

    _buildObjectToUnitMap_lvl1()
    print('  -- Level 1: Object map complete!')
    _buildObjectToUnitMap_lvl2()
    print('  -- Level 2: Object map complete!')
    _buildObjectToUnitMap_lvl3()
    print('  -- Level 3: Object map complete!\n')
#enddef

def _buildObjectToUnitMap_lvl1():
    global FOON_objectsToUnits_lvl1, nodes_lvl1, FOON_lvl1
    for N in nodes_lvl1:
        if isinstance(N, FOON.Object):
            procedures = []
            for _U in FOON_outputsToUnits_lvl1[N]:
                procedures.append(_U)
            for _U in FOON_lvl1:
                for _input in _U.getInputList():
                    if _input.equals_functions[0](N):
                        procedures.append(_U); break
                    #endif	
                #endfor
            #endfor
            FOON_objectsToUnits_lvl1[N] = list(set(procedures))
        #endif
    #endfor
    return
#enddef

def _buildObjectToUnitMap_lvl2():
    global FOON_objectsToUnits_lvl2, nodes_lvl2, FOON_lvl2
    for N in nodes_lvl2:
        if isinstance(N, FOON.Object):
            procedures = []
            for _U in FOON_outputsToUnits_lvl2[N]:
                procedures.append(_U)
            for _U in FOON_lvl2:
                for _input in _U.getInputList():
                    if _input.equals_functions[1](N):
                        procedures.append(_U); break
                    #endif	
                #endfor
            #endfor
            FOON_objectsToUnits_lvl2[N] = list(set(procedures))
        #endif
    #endfor
    return
#enddef

def _buildObjectToUnitMap_lvl3():
    global FOON_objectsToUnits_lvl3, FOON_outputsToUnits_lvl3 ,nodes_lvl3, FOON_lvl3
    for N in nodes_lvl3:
        if isinstance(N, FOON.Object):
            procedures = []
            for _U in FOON_outputsToUnits_lvl3[N]:
                procedures.append(_U)
            #endfor
            for _U in FOON_lvl3:
                for _input in _U.getInputList():
                    if _input.equals_functions[2](N):
                        procedures.append(_U); break
                    #endif	
                #endfor
            #endfor
            FOON_objectsToUnits_lvl3[N] = list(set(procedures))
        #endif
    #endfor
    return
#enddef

def _buildFunctionalUnitMap():
    # NOTE: create a mapping between functional units to show 
    # 	which ones are connected to one another.
    print(' -- [FOON-fga] : Building FU-to-FU dictionaries...')

    _buildUnitToUnitMap_lvl1()
    print('  -- Level 1: Functional unit map complete!')
    _buildUnitToUnitMap_lvl2()
    print('  -- Level 2: Functional unit map complete!')
    _buildUnitToUnitMap_lvl3()
    print('  -- Level 3: Functional unit map complete!\n')
#enddef	

def _buildUnitToUnitMap_lvl1():
    global FOON_functionalUnitMap_lvl1
    for _FU in FOON_lvl1:
        prerequisite_units = []
        for _input in _FU.getInputList():
            # -- we already collected the units that create every single input object in FOON:
            candidates = FOON_outputsToUnits_lvl1.get(_input, [])

            for C in candidates:
                if FOON_lvl1.index(C) not in prerequisite_units:	
                    prerequisite_units.append(FOON_lvl1.index(C))
        #endfor
        FOON_functionalUnitMap_lvl1[FOON_lvl1.index(_FU)] = prerequisite_units
    #endfor
    return
#enddef

def _buildUnitToUnitMap_lvl2():
    global FOON_functionalUnitMap_lvl2
    for _FU in FOON_lvl2:
        prerequisite_units = []
        for _input in _FU.getInputList():
            # -- we already collected the units that create every single input object in FOON:
            candidates = FOON_outputsToUnits_lvl2.get(_input, [])

            for C in candidates:
                if FOON_lvl2.index(C) not in prerequisite_units:	
                    prerequisite_units.append(FOON_lvl2.index(C))
        #endfor
        FOON_functionalUnitMap_lvl2[FOON_lvl2.index(_FU)] = prerequisite_units
    #endfor
    return
#enddef

def _buildUnitToUnitMap_lvl3():
    global FOON_functionalUnitMap_lvl3
    for _FU in FOON_lvl3:
        prerequisite_units = []
        for _input in _FU.getInputList():
            # -- we already collected the units that create every single input object in FOON:
            candidates = FOON_outputsToUnits_lvl3.get(_input, [])
            for C in candidates:
                if FOON_lvl3.index(C) not in prerequisite_units:	
                    prerequisite_units.append( FOON_lvl3.index(C) )
        #endfor
        FOON_functionalUnitMap_lvl3[FOON_lvl3.index(_FU)] = prerequisite_units
    #endfor
    return
#enddef

def _printObjectToUnitMap(hierarchy_level):
    if hierarchy_level == 1:
        objectMap = FOON_outputsToUnits_lvl1
    elif hierarchy_level == 2:
        objectMap = FOON_outputsToUnits_lvl2
    elif hierarchy_level == 3:
        objectMap = FOON_outputsToUnits_lvl3
    else:
        return

    for _key in objectMap:
        _key.print_functions[hierarchy_level-1]()
        for _FU in objectMap[_key]:
            print("{")
            _FU.print_functions[hierarchy_level-1]()
            print("}\n")
        #endfor
    #endfor
    return
#enddef

def _printFunctionalUnitMap():
    for _key in FOON_functionalUnitMap_lvl3:
        print("SOURCE:")
        _key.print_functions[2]()
        print("\nTARGET(S):")
        for _FU in FOON_functionalUnitMap_lvl3[_key]:
            print("{")
            _FU.print_functions[2]()
            print("}\n")
        #endfor
    #endfor
#enddef

def _readIndexFiles():
    print('\n -- [FOON-fga] : Reading index files...')

    # NOTE: first, try to open combined .JSON file (contains all labels for objects, states, and motions):

    try:
        import json
        FOON_index = json.load( open('FOON_index.json', 'r') )

    except FileNotFoundError:
        print(" -- WARNING: Combined index file 'FOON_index.json' not found in current directory!")
        print("\t-- Using legacy text files instead!")

    else:
        for O in FOON_index['objects']:
            FOON_objectLabels[O] = int(FOON_index['objects'][O]['id'])
            if 'sense' in FOON_index['objects'][O]:
                FOON_objectSenses[O] = int(FOON_index['objects'][O]['sense']) if str(FOON_index['objects'][O]['sense']).isdigit() else FOON_index['objects'][O]['sense']
            else:
                FOON_objectSenses[O] = 1

        print('  -- Loaded ' + str(len(FOON_objectLabels)) + ' object labels!')

        for S in FOON_index['states']:
            FOON_stateLabels[S] = int(FOON_index['states'][S]['id'])

        print('  -- Loaded ' + str(len(FOON_stateLabels)) + ' state labels!')

        for M in FOON_index['motions']:
            FOON_motionLabels[M] = int(FOON_index['motions'][M]['id'])

        print('  -- Loaded ' + str(len(FOON_motionLabels)) + ' motion labels!')
        
        return
    #end

    # NOTE: if we get here, that means that we do not have the .JSON file, so just use regular text files:
    try:
        _file = open('FOON-object_index.txt', 'r')
    except FileNotFoundError:
        print(" -- WARNING: File 'FOON-object_index.txt' not found in current directory!")
    else:
        items = _file.read().splitlines()
        for L in items:
            if L.startswith("//"):
                continue
            _parts = L.split("\t")
            FOON_objectLabels[_parts[1]] = int(_parts[0])
            if len(_parts) > 2:
                FOON_objectSenses[_parts[1]] = int(_parts[2]) if str(_parts[2]).isdigit() else _parts[2]
            else:
                FOON_objectSenses[_parts[1]] = 1
        #endfor
        _file.close()
    #end

    try:
        _file = open('FOON-motion_index.txt', 'r')
    except FileNotFoundError:
        print(" -- WARNING: File 'FOON-motion_index.txt' not found in current directory!")
    else:
        items = _file.read().splitlines()
        for L in items:
            if L.startswith("//"):
                continue
            _parts = L.split("\t")
            FOON_motionLabels[_parts[1]] = int(_parts[0])
        #endfor
        _file.close()
    #end

    try:
        _file = open('FOON-state_index.txt', 'r')
    except FileNotFoundError:
        print(" -- WARNING: File 'FOON-state_index.txt' not found in current directory!")
    else:
        items = _file.read().splitlines()
        for L in items:
            if L.startswith("//"):
                continue
            _parts = L.split("\t")
            FOON_stateLabels[_parts[1]] = int(_parts[0])
        #endfor
        _file.close()
    #end
    
    return
#enddef

###############################################################################################################################

# NOTE: network centrality algorithms for analysis:
def _buildOneModeProjections(hierarchy_level=None):
    # NOTE: purpose of the function is to create one-mode projection of FOON at all levels:
    if not hierarchy_level:
        # -- just build them all...
        _buildOneModeProjection_lvl1()
        _buildOneModeProjection_lvl2()
        _buildOneModeProjection_lvl3()
    elif hierarchy_level == 1:
        _buildOneModeProjection_lvl1()
    elif hierarchy_level == 2:
        _buildOneModeProjection_lvl2()
    elif hierarchy_level == 3:
        _buildOneModeProjection_lvl3()
    else:
        return
#enddef	

def _buildOneModeProjection_lvl1():
    global objects_oneModeProjection_lvl1, FOON_oneModeProjection_lvl1
    for _node in objects_oneModeProjection_lvl1:
        source = objects_oneModeProjection_lvl1.index(_node)
        dest = set()
        for _motion in _node.getNeighbourList():
            for _output in _motion.getNeighbourList():
                dest.add(objects_oneModeProjection_lvl1.index(_output))
            #endfor
        #endfor
        FOON_oneModeProjection_lvl1[source] = dest
    #endfor	
#enddef

def _buildOneModeProjection_lvl2():
    global objects_oneModeProjection_lvl2, FOON_oneModeProjection_lvl2
    for _node in objects_oneModeProjection_lvl2:
        source = objects_oneModeProjection_lvl2.index(_node)
        dest = set()
        for _motion in _node.getNeighbourList():
            for _output in _motion.getNeighbourList():
                dest.add(objects_oneModeProjection_lvl2.index(_output))
            #endfor
        #endfor
        FOON_oneModeProjection_lvl2[source] = dest
    #endfor	
#enddef

def _buildOneModeProjection_lvl3():
    global objects_oneModeProjection_lvl3, FOON_oneModeProjection_lvl3
    for _node in objects_oneModeProjection_lvl3:
        source = objects_oneModeProjection_lvl3.index(_node)
        dest = set()
        for _motion in _node.getNeighbourList():
            for _output in _motion.getNeighbourList():
                dest.add(objects_oneModeProjection_lvl3.index(_output))
            #endfor
        #endfor
        FOON_oneModeProjection_lvl3[source] = dest
    #endfor	
#enddef

def _calculateCentrality(hierarchy_level):
    # NOTE: Refer to "Networks: An Introduction" by Mark Newman (more info: https://dl.acm.org/doi/book/10.5555/1809753) 
    # 	for an excellent overview of this algorithm and many other neat graph theory tricks and concepts.

    global file_name, verbose
    try:
        # -- if you don't have NumPy.. then you're gonna have a bad time.
        import numpy as np
    except ImportError:
        print(" -- ERROR: NumPy not found! Please install NumPy to use this function!")
        return
    
    # -- first, we need to get the one-mode projection so that we can interpret the results after:
    objectList = None; searchMap = None
    if hierarchy_level == 1:
        objectList = objects_oneModeProjection_lvl1
        searchMap = FOON_oneModeProjection_lvl1
    elif hierarchy_level == 2:
        objectList = objects_oneModeProjection_lvl2
        searchMap = FOON_oneModeProjection_lvl2
    else:
        objectList = objects_oneModeProjection_lvl3
        searchMap = FOON_oneModeProjection_lvl3

    # -- get adjacency matrix for one-mode projection of FOON:
    oneModeMatrix = _populateAdjacencyMatrix(hierarchy_level)

    # -- determining the dimensions of the adjacency matrix:
    num_elements = oneModeMatrix.shape[1]

    if verbose:
        # -- saving the adjacency matrix to a file for verification:
        np.savetxt("adjacency_matrix.csv", oneModeMatrix, delimiter=",")

    # -- calculate eigenvalues for each object node in FOON:
    eigenvalues, eigenvectors = np.linalg.eig(oneModeMatrix)
    max_index = np.argmax(eigenvalues)
    max_eigenvalue = eigenvalues[max_index]

    max_eigen = 0
    _file = open(os.path.splitext(file_name)[0] + "_eigenvector_lvl" + str(hierarchy_level) +".txt", 'w')
    for E in range(num_elements):
        _file.write(objectList[E].getObjectLabel() + '_' + str(objectList[E].getStatesList()) + "\t" + str(np.real(eigenvectors[max_index][E])) + '\n')
        if eigenvectors[max_index][E] > eigenvectors[max_index][max_eigen]:
            max_eigen = E
    _file.close()

    print('\n -- [NET-CENT] : Object with largest eigenvector centrality value (value=' + str(np.real(eigenvectors[max_index][max_eigen])) + ') is :')
    objectList[max_eigen].print_functions[hierarchy_level-1]()

    # -- necessary values for Katz centrality computation:
    alpha = 1 / (max_eigenvalue + 0.25) 	# NOTE: recommended that it is less than 1/K^1, so 0.25 was added to arbitrarily meet this requirement.
    B = np.ones((num_elements,1))
    I = np.eye(num_elements)
    A = np.subtract(I, np.multiply(oneModeMatrix, alpha))

    # -- calculate Katz centrality, which simplifies to Ax = B (as per 7.10 in Newman):
    X = np.linalg.solve(A, B)
    max_katz = 0
    _file = open(os.path.splitext(file_name)[0] + "_katz_lvl" + str(hierarchy_level) +".txt", 'w')
    for E in range(num_elements):
        _file.write(objectList[E].getObjectLabel() + '_' + str(objectList[E].getStatesList()) + "\t" + str(np.real(X.item(E))) + '\n')
        if X[E] > X[max_katz]:
            max_katz = E
    _file.close()

    # NOTE: Katz centrality : pick the node with the largest computed value in X:
    print('\n -- [NET-CENT] : Object with largest Katz centrality value (katz=' + str(np.real(X[max_katz])) + ') is :')
    objectList[max_katz].print_functions[hierarchy_level-1]()

    # -- calculate degree centrality:
    _file = open(os.path.splitext(file_name)[0] + "_degree_lvl" + str(hierarchy_level) +".txt", 'w')
    max_value = 0
    for E in range(len(objectList)):
        _file.write(objectList[E].getObjectLabel() + '_' + str(objectList[E].getStatesList()) + "\t" + str(len(searchMap[E])) + '\n')
        if len(searchMap[E]) > max_value:
            max_value = len(searchMap[E])
    _file.close()

    max_deg = []
    for x in range(len(objectList)):
        if len(searchMap[x]) == max_value:
            max_deg.append(x)

    print('\n -- [NET-CENT] : Object(s) with largest degree centrality value (n_neighbours = ' + str(max_value) + ') are :')
    for x in max_deg:
        objectList[x].print_functions[hierarchy_level-1]()
        print("------------------")
#enddef

def _populateAdjacencyMatrix(hierarchy_level):
    # NOTE: Refer to "Networks: An Introduction" by Mark Newman (more info: https://dl.acm.org/doi/book/10.5555/1809753) 
    # 	for an excellent overview of this algorithm and many other neat graph theory tricks and concepts.

    global verbose; searchMap = None

    try:
        import numpy as np
    except ImportError:
        print(" -- ERROR: NumPy not found! Please install NumPy to use this function!")
        return

    if hierarchy_level == 1:
        searchMap = FOON_oneModeProjection_lvl1
    elif hierarchy_level == 2:
        searchMap = FOON_oneModeProjection_lvl2
    elif hierarchy_level == 3:
        searchMap = FOON_oneModeProjection_lvl3
    else:
        return

    if not FOON_oneModeProjection_lvl3:
        _buildOneModeProjections(hierarchy_level=hierarchy_level) 

    # -- create an adjacency matrix of size N x N, where N is number of nodes (i.e. both object and motion) :
    oneModeMatrix = np.eye(( len(searchMap) ))
    for src, tgt in searchMap.items():
        for x in tgt:
            oneModeMatrix[src][x] = 1

    if verbose:
        print(' -- [NET-CENT] Adjacency matrix for one-mode projection is as follows:')	
        print(oneModeMatrix)

    return oneModeMatrix
#enddef

###############################################################################################################################

def _printSummary_FOON():
    print(" -> Level 3: # of UNITS - " + str(len(FOON_lvl3)))
    print(" -> Level 2: # of UNITS - " + str(len(FOON_lvl2)))
    print(" -> Level 1: # of UNITS - " + str(len(FOON_lvl1)))
#enddef

def _printSummary_nodes():
    print(" -> TOTAL NUMBER OF NODES : " + str(len(nodes_lvl3)) )
    print(" -> Level 3: # of OBJECT - " + str(len(FOON_outputsToUnits_lvl3)) + "; # of MOTION - " + str(len(nodes_lvl3) - len(FOON_outputsToUnits_lvl3)))
    print(" -> Level 2: # of OBJECT - " + str(len(FOON_outputsToUnits_lvl2)) + "; # of MOTION - " + str(len(nodes_lvl2) - len(FOON_outputsToUnits_lvl2)))
    print(" -> Level 1: # of OBJECT - " + str(len(FOON_outputsToUnits_lvl1)) + "; # of MOTION - " + str(len(nodes_lvl1) - len(FOON_outputsToUnits_lvl1)))
#enddef

def _printSummary_edges():
    total = 0
    for N in nodes_lvl3:
        total += len(N.getNeighbourList())
    #endfor
    print(" -> Level 3: # of EDGES - " + str(total))
    total = 0
    for N in nodes_lvl2:
        total += len(N.getNeighbourList())
    #endfor
    print(" -> Level 2: # of EDGES - " + str(total))
    total = 0
    for N in nodes_lvl1:
        total += len(N.getNeighbourList())
    #endfor
    print(" -> Level 1: # of EDGES - " + str(total))
#endfor

def _printAnyNode(X, hierarchy_level=3):
    if hierarchy_level == 1:
        node = nodes_lvl1[X]
    elif hierarchy_level == 2:
        node = nodes_lvl2[X]
    else:
        node = nodes_lvl3[X]
    if isinstance(node, FOON.Motion):
        node.printMotion()
        return
    node.print_functions[hierarchy_level-1]()
#enddef

def _printAnyFunctionalUnit(X, hierarchy_level=3):
    if hierarchy_level == 1:
        node = FOON_lvl1[X]
    elif hierarchy_level == 2:
        node = FOON_lvl2[X]
    else:
        node = FOON_lvl3[X]
    node.print_functions[hierarchy_level-1]()
#enddef

def _objectFrequencyReport():
    try:
        _file = open('FOON-object_index.txt', 'r')
    except FileNotFoundError:
        print(" -- WARNING: File 'FOON-object_index.txt' not found in current directory!")
        return
    items = _file.read().splitlines()
    frequency = [0] * len(items)

    for FU in FOON_lvl3:
        for _O in FU.getInputList():
        # -- get the motion node for each functional unit and just tally them up:
            frequency[_O.getObjectType()] += 1
    #endfor

    global file_name
    _file = open(os.path.splitext(file_name)[0] + '_FOON_object_frequency_report.txt', 'w')
    
    for x in range(len(items)):
        line = items[x].split("\t")
        # -- write everything to the file..
        _file.write("O" + str(line[0]) + " : " + str(line[1]) + "\t" + str(frequency[x]) + "\n")
    #endfor

    print(" -- Object frequency file has been saved as '" + (os.path.splitext(file_name)[0] + '_FOON_object_frequency_report.txt') + "'.")
    _file.close()

    _file = open(os.path.splitext(file_name)[0] + '_FOON_existent_FOON_objectLabels.txt', 'w')
    for x in range(len(items)):
        line = items[x].split("\t")
        # -- write everything to the file only if there is at least one instance!
        if frequency[x] > 0:
            _file.write("O" + str(line[0]) + " : " + str(line[1]) + "\t" + str(frequency[x]) + "\n")
        #endif
    #endfor
    _file.close()

    _file = open(os.path.splitext(file_name)[0] + '_FOON_existent_object-states.txt', 'w')
    for x in range(len(nodes_lvl3)):
        # -- write everything to the file only if there is at least one instance!
        if isinstance(nodes_lvl3[x], FOON.Object):
            _file.write(nodes_lvl3[x].getObjectText() + "\n" + "//" + "\n")
        #endif
    #endfor
    _file.close()
#enddef

def _motionFrequencyReport():
    try:
        _file = open('FOON-motion_index.txt', 'r')
    except FileNotFoundError:
        print(" -- WARNING: File 'FOON-motion_index.txt' not found in current directory!")
        return
    items = _file.read().splitlines()
    frequency = [0] * len(items)

    for FU in FOON_lvl3:
        # -- get the motion node for each functional unit and just tally them up:
        frequency[FU.getMotion().getMotionType()] += 1
    #endfor

    global file_name
    _file = open(os.path.splitext(file_name)[0] + '_FOON_motion_frequency_report.txt', 'w')
    
    for x in range(len(items)):
        line = items[x].split("\t")
        # -- write everything to the file..
        _file.write("M" + str(line[0]) + " : " + str(line[1]) + "\t" + str(frequency[x]) + "\n")
    #endfor

    print(" -- Motion frequency file has been saved as '" + (os.path.splitext(file_name)[0] + '_FOON_motion_frequency_report.txt') + "'.")
    _file.close()
#enddef

def _stateFrequencyReport():
    try:
        _file = open('FOON-state_index.txt', 'r')
    except FileNotFoundError:
        print(" -- WARNING: File 'FOON-state_index.txt' not found in current directory!")
        return

    items = _file.read().splitlines()
    frequency = [0] * len(items)

    for N in nodes_lvl3:
        if isinstance(N,FOON.Object):
            for x in range(len(N.getStatesList())):
                frequency[int(N.getStateType(x))] += 1
    #endfor

    global file_name
    _file = open(os.path.splitext(file_name)[0] + '_FOON_state_frequency_report.txt', 'w')
    
    for x in range(len(items)):
        line = items[x].split("\t")
        # -- write everything to the file..
        _file.write("S" + str(line[0]) + " : " + str(line[1]) + "\t" + str(frequency[x]) + "\n")
    #endfor

    print(" -- State frequency file has been saved as '" + (os.path.splitext(file_name)[0] + '_FOON_state_frequency_report.txt') + "'.")
    _file.close()
#enddef

###############################################################################################################################

# NOTE: functions used in loading FOON graph from parsing of files:
def _checkIfFUExists(U, H):
    if H == 1:
        if not FOON_lvl1:
            return False
        for _F in FOON_lvl1:
            if _F.equals_lvl1(U):
                return True
        return False
    if H == 2:
        if not FOON_lvl2:
            return False
        for _F in FOON_lvl2:
            if _F.equals_lvl2(U):
                return True
        return False
    if H == 3:
        if not FOON_lvl3:
            return False
        for _F in FOON_lvl3:
            if _F.equals_lvl3(U):
                return True
        return False
    else:
        pass
#enddef

def _checkIfNodeExists(O, H):
    objectExisting = -1
    if H == 1:
        for N in nodes_lvl1:
            if isinstance(N, FOON.Object) and N.equals_functions[H-1](O):
                objectExisting = nodes_lvl1.index(N)		
    elif H == 2:
        for N in nodes_lvl2:
            if isinstance(N, FOON.Object) and N.equals_functions[H-1](O):
                objectExisting = nodes_lvl2.index(N)
    elif H == 3:
        for N in nodes_lvl3:
            if isinstance(N, FOON.Object) and N.equals_functions[H-1](O):
                objectExisting = nodes_lvl3.index(N)
    else:
        pass

    return objectExisting
#enddef	
    
def _constructFOON(file=None):
    # NOTE: entry point function to load a FOON subgraph file, which may either be a .TXT, .PKL or .JSON file:
    global file_name
    if not file:
        file = file_name
    else:
        file_name = file

    print("\n -- [FOON-fga] : Opening FOON file named '"  + str(file) + "'...")

    if '.txt' in file.lower():
        _loadFOON_txt(file)
        FOON.print_old_style = True
    elif '.json' in file.lower():
        # -- give a .JSON file, which is typically larger than the average text file, but it structures things neatly:
        _loadFOON_json(file)
        FOON.print_old_style = False
    elif '.pkl' in file.lower():
        # WARNING: ONLY USE .PKL FILE THAT HAS BEEN PROCESSED ALREADY!!
        # -- users can load a .PKL file containing the structures and references for an already processed universal FOON:
        _loadFOON_pkl(file)
    else:
        print(' -- WARNING: Wrong file type or format!')
        print("  -- Skipping: '" + str(file) + "' ...")
#enddef

def _loadFOON_txt(file=None):
    # NOTE: this is the .TXT file variant of the FOON subgraph loading function:

    # NOTE: 'FOON_node_count' indicates the number of nodes (i.e. both object AND motion nodes) exist in a universal FOON.
    # -- this number is based on the hierarchy level 3.
    global FOON_node_count
    
    global FOON_video_source, verbose
    
    global FOON_lvl1, FOON_lvl2, FOON_lvl3, nodes_lvl1, nodes_lvl2, nodes_lvl3

    stateParts, objectParts, motionParts = [], [], [] # -- objects used to contain the split strings

    # -- isInput - flag used to switch between adding to input or output nodes list for each functional unit
    isInput = True
    
    # -- newObject - this stores an object that is in the process of being read; this is important since we can have multiple AND variable states.
    newObject = None

    # -- objects which will hold the functional unit being read:
    newFU_lvl1, newFU_lvl2, newFU_lvl3 = FOON.FunctionalUnit(), FOON.FunctionalUnit(), FOON.FunctionalUnit()

    _file = open(file, 'r'); items = _file.read().splitlines()

    line_count = 0

    for line in tqdm.tqdm(items, desc='  -- Reading file line '):	
        line_count += 1

        # -- checking flag for verbose (print-outs):
        if verbose:
            print('line ' + str(line_count) + ' - ' + line)

        try:

            if line.startswith("# Source:"):
                line = line.split('\t')
                FOON_video_source.append(line[1].strip('\n'))

            elif line.startswith("//"):
                if newObject:
                    # -- the last output object is not added right away since we need to see if we do not know how many states we are expecting:
                    _addObjectToFOON(newObject, isInput, objectParts[2], newFU_lvl3, newFU_lvl2, newFU_lvl1)

                if newFU_lvl3.isEmpty():
                    # -- this means that we did not add anything to this functional unit object, so just continue:
                    continue

                # -- we are adding a new FU, so start from scratch..
                if _checkIfFUExists(newFU_lvl3, 3) == False:
                    # NOTE: no matter what, we add new motion nodes; we will have multiple instances everywhere.	
                    nodes_lvl3.append(newFU_lvl3.getMotion())
                    FOON_lvl3.append(newFU_lvl3)
                    motionsToFunctionalUnits_lvl3[nodes_lvl3.index(newFU_lvl3.getMotion())] = newFU_lvl3
                    # -- we only keep track of the total number of nodes in the LVL3 FOON.
                    FOON_node_count += 1

                if _checkIfFUExists(newFU_lvl2, 2) == False:
                    nodes_lvl2.append(newFU_lvl2.getMotion())
                    FOON_lvl2.append(newFU_lvl2)
                    motionsToFunctionalUnits_lvl2[nodes_lvl2.index(newFU_lvl2.getMotion())] = newFU_lvl2

                if _checkIfFUExists(newFU_lvl1, 1) == False:
                    nodes_lvl1.append(newFU_lvl1.getMotion())
                    FOON_lvl1.append(newFU_lvl1)
                    motionsToFunctionalUnits_lvl1[nodes_lvl1.index(newFU_lvl1.getMotion())] = newFU_lvl1

                # -- create an entirely new FU object to proceed with reading new units.			
                newFU_lvl1, newFU_lvl2, newFU_lvl3 = FOON.FunctionalUnit(), FOON.FunctionalUnit(), FOON.FunctionalUnit()

                # -- this is the end of a FU so we will now be adding input nodes; set flag to TRUE.
                isInput = True; newObject = None

            elif line.startswith("O"):
                # -- we have an Object already in consideration which we were appending states to:
                if newObject:
                    _addObjectToFOON(newObject, isInput, objectParts[2], newFU_lvl3, newFU_lvl2, newFU_lvl1)
                # -- this is an Object node, so we probably should read the next line one time
                # -- get the Object identifier by splitting first instance of O
                objectParts = line.split("O"); objectParts = objectParts[1].split("\t")
                newObject = FOON.Object(objectID=int(objectParts[0]), objectLabel=objectParts[1])

                # -- checking if an object is marked as intended goal of a subgraph file:
                if '!' in line:
                    newObject.setAsGoal()

            elif line.startswith("S"):
                # -- get the Object's state identifier by splitting first instance of S
                stateParts = line.split("S"); stateParts = stateParts[1].split("\t"); stateParts = list(filter(None, stateParts))

                # -- check if this object is a container:
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
                            list_ingredients.sort()
                    elif '[' in stateParts[2]:
                        # NOTE: a geometrically-related object will be enclosed in square brackets:

                        # -- mention of geometrically-relative object:
                        relater = [ stateParts[2] ]
                        relater = relater[0].split("[")
                        relater = relater[1].split("]")
                        relative_object = relater[0]
                    else:
                        pass

                newObject.addNewState([int(stateParts[0]), stateParts[1], relative_object])

                if list_ingredients:
                    newObject.setIngredients(list_ingredients)

            elif line.startswith("M"):
                if newObject:
                    _addObjectToFOON(newObject, isInput, objectParts[2], newFU_lvl3, newFU_lvl2, newFU_lvl1)
                newObject = None

                # -- We are adding a Motion node, so very easy to deal with, as follows:
                motionParts = line.split("M")				# -- get the Motion number...
                motionParts = list(filter(None, motionParts[1].split("\t")))	#  ... and get the Motion label

                # Functional Unit - Level 3:
                # -- create new Motion based on what was read:
                newMotion = FOON.Motion(motionID=int(motionParts[0]), motionLabel=motionParts[1])

                for T in newFU_lvl3.getInputList():
                    T.addNeighbour(newMotion) # -- make the connection from Object(s) to Motion

                newFU_lvl3.setMotion(newMotion)
                
                start_time, end_time = None, None
                success_rate, weighted_entity = None, None

                # -- check if we have the old or new format of the times:
                if '<' in line or '>' in line:
                    # -- we will have the format <XXX,YYY> or <Assumed>:
                    motionTimes = motionParts[2].split('<')[1].split('>')[0].split(',')
                    if len(motionTimes) > 1:
                        start_time = motionTimes[0]
                        end_time = motionTimes[1]

                    # -- this is to check for the new version of FOON with robot/human difficulties:
                    if len(motionParts) > 3:
                        weighted_entity = motionParts[3]; success_rate = motionParts[4]
                        # -- this will indicate whether motion is done by robot or human
                    #endif
                else:
                    # -- we will have regular tab-separated format:
                    start_time = motionParts[2]
                    end_time = motionParts[3]

                    # -- this is to check for the new version of FOON with robot/human difficulties:
                    if len(motionParts) > 4:
                        # -- this will indicate whether motion is done by robot or human
                        weighted_entity = motionParts[4]; success_rate = motionParts[5]
                    #endif
                #endif

                if start_time and end_time:
                    newFU_lvl3.setTimes(start_time, end_time)

                if success_rate:
                    newFU_lvl3.setSuccessRate(float(success_rate))

                if weighted_entity:	
                    newFU_lvl3.setIndication(weighted_entity)

                # Functional Unit - Level 2:
                newMotion = FOON.Motion(motionID=int(motionParts[0]), motionLabel=motionParts[1])

                for T in newFU_lvl2.getInputList():
                    T.addNeighbour(newMotion)

                newFU_lvl2.setMotion(newMotion)
                if start_time and end_time:
                    newFU_lvl2.setTimes(start_time, end_time)

                if success_rate:
                    newFU_lvl2.setSuccessRate(float(success_rate))

                if weighted_entity:	
                    newFU_lvl2.setIndication(weighted_entity)

                # Functional Unit - Level 1:
                newMotion = FOON.Motion(motionID=int(motionParts[0]), motionLabel=motionParts[1])

                for T in newFU_lvl1.getInputList():
                    T.addNeighbour(newMotion)

                newFU_lvl1.setMotion(newMotion)
                if start_time and end_time:
                    newFU_lvl1.setTimes(start_time, end_time)

                if success_rate:
                    newFU_lvl1.setSuccessRate(float(success_rate))

                if weighted_entity:	
                    newFU_lvl1.setIndication(weighted_entity)

                isInput = False	# -- we will now switch over to adding output nodes since we have seen a motion node
            else:
                pass

            #endif

        except Exception:
            sys.exit('\t-- ERROR: line ' + str(line_count) + ' - ' + line)

        #endtry

    #endfor

    _file.close() 	# -- Don't forget to close the file once we are done!
#enddef

def _loadFOON_json(file=None):
    # NOTE: this is the .JSON file variant of the FOON loading function:

    # -- if you don't have this for some reason.. you're gonna have a bad time.
    try:
        import json
    except ImportError:
        return

    # -- 'FOON_node_count' gives an indication of the number of object AND motion nodes are in FOON.
    global FOON_node_count

    global FOON_video_source, verbose
    
    global FOON_lvl1, FOON_lvl2, FOON_lvl3, nodes_lvl1, nodes_lvl2, nodes_lvl3

    # -- objects which will hold the functional unit being read:
    newFU_lvl1, newFU_lvl2, newFU_lvl3 = FOON.FunctionalUnit(), FOON.FunctionalUnit(), FOON.FunctionalUnit()

    _file = open(file, 'r'); _json = json.load(_file)
    for func_unit in _json['functional_units']:	

        # -- checking flag for verbose (print-outs):
        if verbose:
            print(func_unit)

        for _input in func_unit['input_nodes']:
            # -- level 3 version:
            newObject = FOON.Object(objectID=int(_input['object_id']), objectLabel=_input['object_label'])
            for S in _input['object_states']:
                if 'relative_object' in S:
                    newObject.addNewState( [ int(S['state_id']), S['state_label'], S['relative_object'] ] )
                else:
                    newObject.addNewState( [ int(S['state_id']), S['state_label'], None ] )

            for I in _input['ingredients']:
                # NOTE: in the new JSON format, it is easy to assign objects to objects as ingredients; in this way, object nodes could possibly be recursive.

                # NOTE: to use this, set 'flag_recursive_objects' to True
                # -- HOWEVER, you must have the files annotated with this format!
                if FOON.flag_recursive_objects:
                    newIngredient = FOON.Object(objectID=int(I['object_id']), objectLabel=I['object_label'])
                    for S in I['object_states']:
                        if 'relative_object' in S:
                            newObject.addNewState( [ int(S['state_id']), S['state_label'], S['relative_object'] ] )
                        else:
                            newObject.addNewState( [ int(S['state_id']), S['state_label'], None ] )

                    # -- objects contained within objects may already be used in other ways, so it is important to note if
                    #	they already exist in FOON.
                    newIngredient = _addIngredientToFOON(newIngredient)
                    newObject.addIngredient(newIngredient)
                else:
                    # -- if not, just stick to object-label-only ingredients as done before
                    newObject.addIngredient(I)
            
            _addObjectToFOON(newObject, True, _input['object_in_motion'], newFU_lvl3, newFU_lvl2, newFU_lvl1)

        # NOTE: reading motion node information:
        # -- level 1 version:
        newMotion = FOON.Motion(motionID=int(func_unit['motion_node']['motion_id']), motionLabel=func_unit['motion_node']['motion_label'])
        for T in newFU_lvl3.getInputList():
            T.addNeighbour(newMotion) # -- make the connection from Object(s) to Motion
        newFU_lvl3.setMotion(newMotion); newFU_lvl3.setTimes(func_unit['motion_node']['start_time'], func_unit['motion_node']['end_time'])

        # -- this is to check for the new version of FOON with robot/human difficulties:
        if func_unit['motion_node'].get('weight_success', None):
            # -- this will indicate whether motion is done by robot or human
            newFU_lvl3.setIndication(func_unit['motion_node']['robot_type']); newFU_lvl3.setSuccessRate(float(func_unit['motion_node']['weight_success']))

        # -- level 2 version:
        newMotion = FOON.Motion(motionID=int(func_unit['motion_node']['motion_id']), motionLabel=func_unit['motion_node']['motion_label'])
        for T in newFU_lvl2.getInputList():
            T.addNeighbour(newMotion) # -- make the connection from Object(s) to Motion
        newFU_lvl2.setMotion(newMotion); newFU_lvl2.setTimes(func_unit['motion_node']['start_time'], func_unit['motion_node']['end_time'])

        if func_unit['motion_node'].get('weight_success', None):
            # -- this will indicate whether motion is done by robot or human
            newFU_lvl2.setIndication(func_unit['motion_node']['robot_type']); newFU_lvl2.setSuccessRate(float(func_unit['motion_node']['weight_success']))

        # -- level 1 version:
        newMotion = FOON.Motion(motionID=int(func_unit['motion_node']['motion_id']), motionLabel=func_unit['motion_node']['motion_label'])
        for T in newFU_lvl1.getInputList():
            T.addNeighbour(newMotion) # -- make the connection from Object(s) to Motion
        newFU_lvl1.setMotion(newMotion); newFU_lvl1.setTimes(func_unit['motion_node']['start_time'], func_unit['motion_node']['end_time'])

        if func_unit['motion_node'].get('weight_success', None):
            # -- this will indicate whether motion is done by robot or human
            newFU_lvl1.setIndication(func_unit['motion_node']['robot_type']); newFU_lvl1.setSuccessRate(float(func_unit['motion_node']['weight_success']))

        for _output in func_unit['output_nodes']:
            # -- level 3 version:
            newObject = FOON.Object(objectID=int(_output['object_id']), objectLabel=_output['object_label'])
            for S in _output['object_states']:
                if 'relative_object' in S:
                    newObject.addNewState( [ int(S['state_id']), S['state_label'], S['relative_object'] ] )
                else:
                    newObject.addNewState( [ int(S['state_id']), S['state_label'], None ] )

            for I in _output['ingredients']:
                # NOTE: in the new JSON format, it is easy to assign objects to objects as ingredients; in this way, object nodes could possibly be recursive.

                # NOTE: to use this, set 'flag_recursive_objects' to True
                # -- HOWEVER, you must have the files annotated with this format!
                if FOON.flag_recursive_objects is True:
                    newIngredient = FOON.Object(objectID=int(I['object_id']), objectLabel=I['object_label'])
                    for S in I['object_states']:
                        if 'relative_object' in S:
                            newObject.addNewState( [ int(S['state_id']), S['state_label'], S['relative_object'] ] )
                        else:
                            newObject.addNewState( [ int(S['state_id']), S['state_label'], None ] )

                    # -- objects contained within objects may already be used in other ways, so it is important to note if
                    #	they already exist in FOON.
                    newIngredient = _addIngredientToFOON(newIngredient)
                    newObject.addIngredient(newIngredient)
                else:
                    # -- if not, just stick to object-label-only ingredients as done before
                    newObject.addIngredient(I)

            _addObjectToFOON(newObject, False, _output['object_in_motion'], newFU_lvl3, newFU_lvl2, newFU_lvl1)

        if _checkIfFUExists(newFU_lvl3, 3) == False:
            # NOTE: no matter what, we add new motion nodes; we will have multiple instances everywhere.		
            nodes_lvl3.append(newFU_lvl3.getMotion())
            FOON_lvl3.append(newFU_lvl3)
            motionsToFunctionalUnits_lvl3[nodes_lvl3.index(newFU_lvl3.getMotion())] = newFU_lvl3
            
            # -- we only keep track of the total number of nodes in the LVL3 FOON.
            FOON_node_count += 1

        if _checkIfFUExists(newFU_lvl2, 2) == False:
            nodes_lvl2.append(newFU_lvl2.getMotion())
            FOON_lvl2.append(newFU_lvl2)
            motionsToFunctionalUnits_lvl2[nodes_lvl2.index(newFU_lvl2.getMotion())] = newFU_lvl2

        if _checkIfFUExists(newFU_lvl1, 1) == False:
            nodes_lvl1.append(newFU_lvl1.getMotion())
            FOON_lvl1.append(newFU_lvl1)
            motionsToFunctionalUnits_lvl1[nodes_lvl1.index(newFU_lvl1.getMotion())] = newFU_lvl1
            
        # -- create an entirely new FU object to proceed with reading new units.			
        newFU_lvl1, newFU_lvl2, newFU_lvl3 = FOON.FunctionalUnit(), FOON.FunctionalUnit(), FOON.FunctionalUnit()
    
    #endfor

    _file.close() 	# -- Don't forget to close the file once we are done!
#enddef

def _loadFOON_pkl(file=None):
    import pickle

    global FOON_functionalUnits, FOON_lvl1, FOON_lvl2, FOON_lvl3
    global FOON_nodes, nodes_lvl1, nodes_lvl2, nodes_lvl3

    print(' -- [PKL_to_FOON] : Loading FOON (nodes and functional units) from .PKL file...')

    if not file:
        file = 'FOON.pkl'

    with open(file, 'rb') as F:
        FOON_nodes, FOON_functionalUnits = pickle.load(F)

    # -- load the main lists that are needed for FOON to operate:
    nodes_lvl1, nodes_lvl2, nodes_lvl3 = FOON_nodes[0], FOON_nodes[1], FOON_nodes[2]
    FOON_lvl1, FOON_lvl2, FOON_lvl3 = FOON_functionalUnits[0], FOON_functionalUnits[1], FOON_functionalUnits[2]

    print(' -- [PKL_to_FOON] : Completed loading of .PKL file!')
    print('\n -- Now running internal map building function...')

    # -- best to run the following function now to build all required dictionaries:
    _buildInternalMaps()

    return
#enddef

def _saveFOON_txt(file_name=None, post_merge=True, skip_PKL=False):
    global verbose, config, FOON_lvl3, FOON_video_source

    # -- check config file for possible name for universal FOON or use default name:
    if config.sections():
        merged_file = config['Paths']['universal_FOON']
    elif file_name:
        merged_file = file_name
    else:
        merged_file = 'universal_FOON.txt'

    _file = open(merged_file, 'w')
    
    print(" -- [FOON_to_TXT] : Saving new universal FOON as file '" + (merged_file) + "' ...")
    if verbose:
        print("\n -- [FOON_to_TXT] : Merged FOON functional units as follows:")

    if not post_merge:
        # -- write the source link for the FOON subgraph (if available):
        for _source in FOON_video_source:
            _file.write('# Source:\t' + str(_source) + '\n')

    # -- write timestamp of when file was created for record-keeping:
    from datetime import datetime

    _file.write('# Date created:\t' + str(datetime.today().strftime('%d.%m.%Y')) + '\n')
    _file.write('//\n')

    # -- append strings for each functional unit together and then write to a file after:
    _unit = str()
    for FU in FOON_lvl3:
        if verbose:
            FU.print_functions[2]()
            print("//")
        _unit += FU.getFunctionalUnitText()
    _file.write(_unit)
    _file.close()

    if not skip_PKL:
        _saveFOON_pkl(merged_file)

    # -- return the name of the merged file:
    return merged_file
#enddef

def _saveFOON_pkl(file=None):
    try:
        import pickle
    except ImportError:
        print(' -- ERROR: Missing pickle library!')
        return

    print(' -- [FOON_to_PKL] : Saving FOON (nodes and functional units) as .PKL file...')

    global FOON_nodes, FOON_functionalUnits, file_name
    
    if not file:
        file = os.path.splitext(file_name)[0] + '.pkl'
    elif file.endswith('.txt'):
        file = os.path.splitext(file)[0] + '.pkl'
    #endif

    # -- we can probably pickle both functional unit lists and node lists separately:
    while True:
        try:
            with open(file, 'wb') as F:
                pickle.dump((FOON_nodes, FOON_functionalUnits), F)
            
            print(" -- [FOON_to_PKL] : Pickle file for FOON stored as 'FOON.pkl'!")
            break

        except RecursionError:
            # -- prompt user if they mind increasing recursion limit to save this universal FOON:
            response = input(' 	-- ERROR: Python requires higher recursion limit to save FOON objects (default - 1000; current - ' + str(sys.getrecursionlimit()) + ')!' +
                        '\n  -- Would you like to try raising the recursion limit? [Y/N] (Default: Y) > ')
            if response == 'N':
                print('  -- [FOON_to_PKL] : File not saved; terminating pickle file dumping process...')
                break
            
            # -- conservatively increase the recursion limit..
            sys.setrecursionlimit( sys.getrecursionlimit() + 200)
            print('\033[A\033[A')
        #end
    #endwhile

    return
#enddef

def _saveFOON_JS():
    print(' -- [FOON_to_JS] : Saving FOON (nodes and functional units) as .JS file...')

    # -- first, read the current file and then split it into separate lines:
    global file_name
    _file = open(file_name, 'r')
    items = _file.read().splitlines()

    # -- now, go ahead and open the new file containing the Javascript version of the FOON:
    _file = open(os.path.splitext(file_name)[0] + '.js', 'w')
    _file.write("var FOON_graph = [")

    for line in items:
        _file.write("\"" + line + "\"")
        _file.write(",\n")
    #endfor
        
    _file.write("];")
    _file.close()
#enddef

def _saveFOON_json():

    print(' -- [FOON_to_JSON] : Saving FOON (nodes and functional units) as .JSON file...')

    try:
        import json
    except ImportError:
        return

    global FOON_video_source, FOON_lvl3, file_name

    # -- create a dictionary to store each functional unit:
    subgraph_units = {}
    subgraph_units['functional_units'] = []

    for FU in FOON_lvl3:
        # -- use function already defined in FOON_classes.py file:
        subgraph_units['functional_units'].append( FU.getFunctionalUnitJSON() )
    if FOON_video_source:
        subgraph_units['source'] = FOON_video_source

    json_file_name = os.path.splitext(file_name)[0] + '.json'

    # -- dump all the contents in dictionary as .JSON:
    json.dump(subgraph_units, open(json_file_name, 'w'), indent=7)
#enddef

# NOTE: universal FOON merging operation:
def _mergeSubgraphs():
    
    global verbose

    # -- first, give the directory for merging:
    directory = None
    if config.sections():
        # -- check if there is a config file that contains details for FOON functionality:
        directory = config['Paths']['data_source']
    else:
        directory = input(" -- [FOON_MERGE] : Please enter the DIRECTORY with files to be merged with the current FOON: > ")
    
    for root, _, files in os.walk(os.path.abspath(directory)):
        for file in files:
            _file =  os.path.join(root, file)
            print("  -- merging: '" + str(_file) + "' ...")
            _constructFOON(_file)
            motions = [F for F in nodes_lvl3 if isinstance(F, FOON.Motion)]
            if verbose:
                print(str(len(nodes_lvl3) - len(motions)) + "," + str(len(motions)))
                
    print(' -- [FOON_MERGE] : Total sum of nodes: ' + str(FOON_node_count) + '\n')
#enddef

###############################################################################################################################

def _identifyKitchenItems(file='FOON-input_only_nodes.txt'):
    try:
        import FOON_retrieval as frt
    except ImportError:
        print(" -- ERROR: Missing 'FOON_retrieval.py' file!")
        print('\t-- This module contains the code for all the retrieval operations.')
        print('\t-- Download here: https://bitbucket.org/davidpaulius/foon_api/src/master/')
        return []
    else:
        # -- make a copy of the lists needed for retrieval operations:
        frt._copyDicts({'fu_list' : FOON_functionalUnits, 
                'nodes_list' : FOON_nodes, 
                'outputs_to_fu' : FOON_outputsToUnits, 
                'objs_to_fu' : FOON_objectsToUnits, 
                'fu_to_fu' : FOON_functionalUnitMap,
                'labels' : FOON_labels} )
                
        return frt._loadKitchenList(file)
    #endtry
#enddef

def _addIngredientToFOON(newIngredient):
    # -- function to check if ingredients (which can exist as individual nodes) already exist within FOON:
    global FOON_node_count

    objectExisting, objectIndex = _checkIfNodeExists(newIngredient, 3), -1
    if  objectExisting == -1:
        # -- just add new object to the list of all nodes
        nodes_lvl3.append(newIngredient)
        objectIndex = FOON_node_count
        objects_oneModeProjection_lvl3.append(nodes_lvl3[objectIndex])
        FOON_node_count += 1
    else:
        objectIndex = objectExisting
    return nodes_lvl3[objectIndex]
#enddef

def _addObjectToFOON(newObject, isInput, D, newFU_lvl3, newFU_lvl2, newFU_lvl1):
    # -- check if object already exists within the list so as to avoid duplicates
    global FOON_node_count, nodes_lvl1, nodes_lvl2, nodes_lvl3

    objectExisting = _checkIfNodeExists(newObject, 3)
    if objectExisting == -1:
        # -- just add new object to the list of all nodes
        nodes_lvl3.append(newObject)
        objectIndex = FOON_node_count
        objects_oneModeProjection_lvl3.append(nodes_lvl3[objectIndex])
        FOON_node_count += 1
    else:
        objectIndex = objectExisting

    if isInput == True:
        # -- this Object will be an input node to the FU:
        newFU_lvl3.addObjectNode(objectNode=nodes_lvl3[objectIndex], is_input=True, is_active_motion=int(D))
    else:
        # -- add the Objects as output nodes to the FU:
        newFU_lvl3.addObjectNode(objectNode=nodes_lvl3[objectIndex], is_input=False, is_active_motion=int(D))
        # -- make the connection from Motion to Object
        newFU_lvl3.getMotion().addNeighbour(nodes_lvl3[objectIndex])

    object_ID = newObject.getObjectType(); object_label = newObject.getObjectLabel()

    # NOTE: Creating level 2 version of this node:
    newObject_lvl2 = FOON.Object(objectID=object_ID, objectLabel=object_label)

    for I in newObject.getStatesList():
        newObject_lvl2.addNewState([int(I[0]), str(I[1]), I[2]])

    objectExisting = _checkIfNodeExists(newObject_lvl2, 2)

    # -- check if object already exists within the list so as to avoid duplicates
    if objectExisting == -1:
        # -- just add new object to the list of all nodes
        objectIndex = len(nodes_lvl2)
        nodes_lvl2.append(newObject_lvl2)
        objects_oneModeProjection_lvl2.append(nodes_lvl2[objectIndex])
    else:
        objectIndex = objectExisting

    if isInput == True:
        newFU_lvl2.addObjectNode(nodes_lvl2[objectIndex], is_input=True, is_active_motion=int(D))
    else:
        newFU_lvl2.addObjectNode(nodes_lvl2[objectIndex], is_input=False, is_active_motion=int(D))
        newFU_lvl2.getMotion().addNeighbour(nodes_lvl2[objectIndex])

    # NOTE: Creating level 1 version of this node:
    newObject_lvl1 = FOON.Object(objectID=object_ID, objectLabel=object_label)

    objectExisting = _checkIfNodeExists(newObject_lvl1, 1)

    # -- check if object already exists within the list so as to avoid duplicates
    if objectExisting == -1:
        objectIndex = len(nodes_lvl1)
        nodes_lvl1.append(newObject_lvl1)
        objects_oneModeProjection_lvl1.append(nodes_lvl1[objectIndex])
    else:
        objectIndex = objectExisting

    if isInput == True:
        newFU_lvl1.addObjectNode(nodes_lvl1[objectIndex], is_input=True, is_active_motion=int(D))
    else:
        newFU_lvl1.addObjectNode(nodes_lvl1[objectIndex], is_input=False, is_active_motion=int(D))
        newFU_lvl1.getMotion().addNeighbour(nodes_lvl1[objectIndex])
#enddef

def _resetFOON(reload=False):
    # NOTE: this function simply resets all lists and structures to empty:

    global FOON_lvl1, FOON_lvl2, FOON_lvl3, FOON_functionalUnits
    FOON_lvl1 = []; FOON_lvl2 = []; FOON_lvl3 = []; FOON_functionalUnits = [FOON_lvl1, FOON_lvl2, FOON_lvl3]

    global nodes_lvl1, nodes_lvl2, nodes_lvl3, FOON_nodes
    nodes_lvl1 = []; nodes_lvl2 = []; nodes_lvl3 = []
    
    FOON_nodes = [nodes_lvl1, nodes_lvl2, nodes_lvl3]

    global FOON_node_count; FOON_node_count = 0

    global FOON_video_source; FOON_video_source = []

    global file_name

    if reload:
        _constructFOON(file_name)
        _buildInternalMaps()
#enddef

def _resetMaps():
    global FOON_functionalUnitMap_lvl1, FOON_outputsToUnits_lvl1
    FOON_functionalUnitMap_lvl1, FOON_outputsToUnits_lvl1 = {}, {}

    global FOON_functionalUnitMap_lvl2, FOON_outputsToUnits_lvl2
    FOON_functionalUnitMap_lvl2, FOON_outputsToUnits_lvl2 = {}, {}

    global FOON_functionalUnitMap_lvl3, FOON_outputsToUnits_lvl3
    FOON_functionalUnitMap_lvl3, FOON_outputsToUnits_lvl3 = {}, {}

    global FOON_outputsToUnits;	FOON_outputsToUnits = [FOON_outputsToUnits_lvl1, FOON_outputsToUnits_lvl2, FOON_outputsToUnits_lvl3]

    global motionsToFunctionalUnits_lvl1, motionsToFunctionalUnits_lvl2, motionsToFunctionalUnits_lvl3, motionsToFunctionalUnits
    motionsToFunctionalUnits_lvl1 = {}; motionsToFunctionalUnits_lvl2 = {}; motionsToFunctionalUnits_lvl3 = {}
    
    motionsToFunctionalUnits = [motionsToFunctionalUnits_lvl1, motionsToFunctionalUnits_lvl2, motionsToFunctionalUnits_lvl3]
#enddef

def _findFunctionalUnitClusters(hierarchy_level=None):
    # NOTE: the purpose of this function is to find chains of functional units which can be compressed into (what we coin as)
    #	"combinational" functional units, which act as a major hub for when ingredients are being added into a container or structure.
    # -- this will be vital when it comes to the *task tree adaptation* problem, which we are currently exploring for deriving truly novel sequences.

    global FOON_functionalUnits, FOON_unitClusters, FOON_nodes, FOON_outputsToUnits

    # -- identify motions that suggest transfer or movement of objects from one point to another:
    transfer_motion_labels = ['pick-and-place', 'place', 'pour', 'sprinkle', 'add', 'scoop', 'grind']
    
    # -- for a certain level of FOON, we need to iterate through the units to find any that could be condensed into a single, larger hub unit.
    for level in range(len(FOON_functionalUnits)):
        # -- if we only want to load a specific level of FOON, then we skip the other levels:
        if hierarchy_level and hierarchy_level != level + 1:
            continue

        current_FOON = FOON_functionalUnits[level]

        clustered_units = []; clustered_unit_map = {}

        # -- we start with the second unit, and we evaluate whether it can merge it with the previous unit (i.e. the first), 
        # 	and we keep exploring and comparing every n-th unit to its (n-1)-th unit till the end.
        # -- or should we start at the end and then bubble all the way to the top?
        for index in range(len(current_FOON) - 1,  0, -1):

            print('do')
            related_units = []

            for _input in current_FOON[index].getInputNodes():
                if _input.hasIngredients() and _input in FOON_outputsToUnits[level]:
                    for N in FOON_outputsToUnits[level][_input]:
                        related_units.append(N)

            for _unit in related_units:
                _unit.print_functions[level]()
                input()
                if current_FOON[index].getMotionNode().getMotionLabel() in transfer_motion_labels \
                    and _unit.getMotionNode().getMotionLabel() in transfer_motion_labels:
                    print('re')

                    # -- check if there is overlap of objects in the input of N-th unit and the output of the (N-1)-th unit:
                    overlapping_nodes = list(set(current_FOON[index].getInputNodes()) & set(_unit.getOutputNodes()))

                    if overlapping_nodes:
                        print('mi')
                        truly_overlapping = False
                        containers = []

                        for O in overlapping_nodes:
                            O.print_functions[level]()
                            print(len(O.getIngredients()))
                            print(O.getIngredients())

                        print()

                        # -- check the nodes' ingredients and see if they truly differ by at least one ingredient:
                        for O in overlapping_nodes:
                            for _input in _unit.getInputNodes():
                                # -- only compare objects that have the same object type/ID:
                                if _input.getObjectType() != O.getObjectType():
                                    continue

                                _input.print_functions[level]()
                                print(_input.getIngredients())
                                print(O.getIngredients())

                                if abs(len(_input.getIngredients()) - len(O.getIngredients())) == 1:
                                    print('fa')
                                    truly_overlapping = True
                                    # -- take note of the containers that suggest overlapping:
                                    containers.append( FOON_nodes[level].index(O) )
                                    containers.append( FOON_nodes[level].index(_input) )
                                    break
                                #endif
                            if truly_overlapping:
                                break
                            #endif

                            #endfor
                        #endfor
                        
                        if truly_overlapping:
                            print('so')
                            # -- let us create the combinational functional unit:
                            new_functional_unit = FOON.FunctionalUnit()
                            new_functional_unit.setMotion( FOON.Motion(motionID=-1, motionLabel='add*') )

                            # -- check if the current functional unit already maps to a cluster:
                            current_FU = clustered_unit_map[current_FOON[index]] if current_FOON[index] in clustered_unit_map else current_FOON[index]
                            prior_FU = clustered_unit_map[_unit] if _unit in clustered_unit_map else _unit				

                            # -- from the PRIOR functional unit, we need to take ALL of the input nodes and we take ALL BUT the container 
                            # 	of the output nodes (i.e., the overlapping node that is present in the CURRENT functional unit):
                            for N in range(prior_FU.getNumberOfInputs()):
                                _input = prior_FU.getInputNodes()[N]
                                new_functional_unit.addObjectNode(objectNode=_input, is_input=True, 
                                                    is_active_motion=prior_FU.getMotionDescriptor(N, is_input=True))

                            for N in range(prior_FU.getNumberOfOutputs()):
                                _output = prior_FU.getOutputNodes()[N]
                                if FOON_nodes[level].index(_output) not in containers:
                                    new_functional_unit.addObjectNode(objectNode=_output, is_input=False, 
                                                        is_active_motion=prior_FU.getMotionDescriptor(N, is_input=False))

                            # -- from the CURRENT functional unit, we need to take ALL of the output nodes and we take ALL BUT the container 
                            # 	of the intput nodes (i.e., the overlapping node that is present in the PRIOR functional unit):
                            for N in range(current_FU.getNumberOfInputs()):
                                _input = current_FU.getInputNodes()[N]
                                if FOON_nodes[level].index(_input) not in containers:
                                    new_functional_unit.addObjectNode(objectNode=_input, is_input=True, 
                                                        is_active_motion=current_FU.getMotionDescriptor(N, is_input=True))

                            for N in range(current_FU.getNumberOfOutputs()):
                                _output = current_FU.getOutputNodes()[N]
                                new_functional_unit.addObjectNode(objectNode=_output, is_input=False, 
                                                    is_active_motion=current_FU.getMotionDescriptor(N, is_input=False))
                            
                            # -- review all functional units that have been previously mapped to a clustered unit:
                            for key in clustered_unit_map:
                                if clustered_unit_map[key] == current_FU:
                                    clustered_unit_map[key] = new_functional_unit

                            clustered_unit_map[current_FOON[index]] = new_functional_unit
                            clustered_unit_map[_unit] = new_functional_unit

                        #endif
                    #endif
                #endif
            #endfor
        #endfor

        # -- now we review all the changes we've made:
        for FU in current_FOON:
            if FU in clustered_unit_map:
                new_unit = clustered_unit_map[FU]
                if new_unit not in clustered_units:
                    clustered_units.append(new_unit)
            else:
                clustered_units.append(FU)

            #endif
        #endfor

        input(len(clustered_units))
        for FU in clustered_units:
            FU.print_functions[level]()
            print('//')

        FOON_unitClusters[level] = clustered_units
    #endfor
#enddef	

def _performTreeRetrieval(searchObject=None, searchState=None):
    try:
        import FOON_retrieval as frt
    except ImportError:
        print(" -- ERROR: Missing 'FOON_retrieval.py' file!")
        print('\t-- This module contains the code for all the retrieval operations.')
        print('\t-- Download here: https://bitbucket.org/davidpaulius/foon_api/src/master/')
        return None
    
    global FOON_functionalUnits, FOON_nodes, FOON_outputsToUnits, FOON_objectsToUnits, FOON_functionalUnitMap, FOON_labels

    # -- make a copy of the lists needed for retrieval operations:
    frt._copyDicts({'goal_object_type' : searchObject,
            'goal_state_type' : searchState,
            'fu_list' : FOON_functionalUnits, 
            'nodes_list' : FOON_nodes, 
            'outputs_to_fu' : FOON_outputsToUnits, 
            'objs_to_fu' : FOON_objectsToUnits, 
            'fu_to_fu' : FOON_functionalUnitMap,
            'labels' : FOON_labels} )

    return frt._startRetrieval()
#enddef

def _performExpansion():
    # -- this dictionary is needed for the expansion techniques:
    _buildObjectToUnitMap()

    try:
        # -- if we want to use expansion again, then we can keep everything loaded (i.e., no importing again):
        if 'FOON_generalization' not in sys.modules:
            import FOON_generalization as fgen
        else:
            fgen = sys.modules['FOON_generalization']
        #end
    except ImportError:
        print(" -- ERROR: Missing 'FOON_generalization.py' file!")
        print('\t-- This module contains the code for all expansion operations.')
        print('\t-- For more information on these approaches, please refer to: https://arxiv.org/abs/1807.02189.')
        print('\t-- Download here: https://bitbucket.org/davidpaulius/foon_api/src/master/')
        return None
    
    global FOON_functionalUnits, FOON_nodes, FOON_outputsToUnits, FOON_objectsToUnits, FOON_functionalUnitMap, FOON_labels, FOON_objectSenses, file_name

    # -- make a copy of the lists needed for expansion operation:
    fgen._copyDicts({'fu_list' : FOON_functionalUnits, 
            'nodes_list' : FOON_nodes, 
            'outputs_to_fu' : FOON_outputsToUnits, 
            'objs_to_fu' : FOON_objectsToUnits, 
            'fu_to_fu' : FOON_functionalUnitMap,
            'labels' : FOON_labels,
            'obj_senses' : FOON_objectSenses,
            'FOON_file_name' : file_name} )

    # -- prepare for expansion by prompting user for parameters to go by (viz. threshold value, method of expansion, etc.)
    _response = input(' -- [FOON-gen] : Expand using 1) text-based method or 2) non-text-based method? [1/2] (default: 1) > ')
    
    expanded_file = fgen._expandNetwork_nontext() if _response == "2" else fgen._expandNetwork_text()

    return expanded_file
#enddef

def _performGeneralization():
    try:
        # -- if we want to use expansion again, then we can keep everything loaded (i.e., no importing again):
        if 'FOON_generalization' not in sys.modules:
            import FOON_generalization as fgen
        else:
            fgen = sys.modules['FOON_generalization']
        #end
    except ImportError:
        print(" -- ERROR: Missing 'FOON_generalization.py' file!")
        print('\t-- This module contains the code for all expansion operations.')
        print('\t-- For more information on these approaches, please refer to: https://arxiv.org/abs/1807.02189.')
        print('\t-- Download here: https://bitbucket.org/davidpaulius/foon_api/src/master/')
        return None
    
    global FOON_functionalUnits, FOON_nodes, FOON_outputsToUnits, FOON_objectsToUnits, FOON_functionalUnitMap, FOON_labels

    # -- make a copy of the lists needed for expansion operation:
    fgen._copyDicts({'fu_list' : FOON_functionalUnits, 
            'nodes_list' : FOON_nodes, 
            'outputs_to_fu' : FOON_outputsToUnits, 
            'objs_to_fu' : FOON_objectsToUnits, 
            'fu_to_fu' : FOON_functionalUnitMap,
            'labels' : FOON_labels} )

    compressed_file = fgen._constructFOON_gen()

#enddef

###############################################################################################################################

# NOTE: miscellaneous operations:
def _startFOONview():
    try:
        import webbrowser
        webbrowser.open('http://foonets.com/FOON_view/visualizer.html')
    except ImportError:
        print(" -- WARNING: Missing 'webbrowser' module for this function!")
        return
    #endtry
#enddef	

def _parseStateClustering(file):
    try:
        cluster_file = open(file, 'r')
    except:
        print(' -- ERROR: there is an issue opening the file!')
    else:
        state_clusters = {}

        lines = cluster_file.readlines()
        for L in lines:
            if L.startswith('#'):
                # -- this means that this line refers to a comment:
                continue

            line_parts = list(filter(None, L.split('\t')))

            # -- the first part will have the cluster name, while the second part has the state labels that fall under it:
            states = []
            for S in list(filter(None, line_parts[1].split(','))):
                states.append(S)

            state_clusters[line_parts[0].rstrip()] = states
        #endfor

        return state_clusters
    #end
    return
#enddef

###############################################################################################################################

# NOTE: functions used to translate functional units into sentences:
# -- sentences are <input_label_1> ... <input_label_k> <motion_label> <output_label_1> ... <output_label_k>
def _FOONtoSentence():
    # -- this function is to generate sentences which can be used for training Word2Vec:
    global file_name
    _file = open(os.path.splitext(file_name)[0] + '_word2vec_sentences.txt', 'w')
    for _FU in FOON_lvl3:
        # -- all this simply does is makes sentences in the form of <input_object_1> ... <input_object_n> <motion> <output_object_1> ... <output_object_n>:
        _file.write(_FU.getWord2VecSentence() + '\n')
    _file.close()
#enddef

def _toLSTMSentences():
    # -- this function is to generate sentences which can be used for LSTM experiment:
    global file_name
    _file = open(os.path.splitext(file_name)[0] + '_to_sentences.txt', 'w')
    for _FU in FOON_lvl3:
        inputs = ''
        for I in _FU.getInputList():
            inputs += I.getObjectLabel(); inputs += ','
        inputs = inputs[:-1]
        _file.write(inputs + '\t' + _FU.getMotion().getMotionLabel() + '\n')
    _file.close()
#enddef

###############################################################################################################################

def _printArgumentsUsage():
    print("ERROR: Unrecognized arguments given to program! Please use from one of the following:")
    print(" --help\t\t\t:- gives an overview of all the flags that work with the program")
    print(" --file='X.txt'\t\t:- open FOON file given as 'X.txt', where X can be any given name")
    print(" --verbose (or --v)\t:- this flag turns on verbose mode, which will result in MANY print-outs for debugging the program")
    print(" --object=X\t\t:- this flag indicates the object type (for searching algorithms)")
    print(" --state=[X, ...]\t:- this flag indicates the object's state(s) (for searching algorithms), provided as a list of numbers")
#enddef

def _displayMenu():
    global last_updated; print("< fga: FOON Graph Analyzer - (last updated " + str(last_updated) + " ) >")
    global file_name; print( ("   --file:'" + str(file_name) + "'") if file_name else '')
    print("\tWhat would you like to do?")
    print("\t\t1.\tMerge multiple subgraphs into universal FOON;")
    print("\t\t2.\tSearch for task tree in FOON;")
    print("\t\t3.\tPrint FOON details (nodes, functional units, motions);")
    print("\t\t4.\tPerform generalization tasks (with FOON-EXP / FOON-GEN);")
    print("\t\t5.\tPerform network centrality on universal FOON;")
    print("\t\t6.\tUse FOON_parser (parsing script for FOON subgraphs);")
    print("\t\t7.\tUse FOON_view (FOON graph visualization tool);")
    print("\t\t8.\tSave universal FOON as other format (.PKL, .JS, .JSON, word2vec);")
    print(); response = input(" -- Please enter your option or press ENTER to exit : [1-8] > ")
    return response
#enddef

def _start():
    # -- command-line argument parsing to put switches:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'v:fi:ob:st', ['verbose', 'file=', "object=", "state=", 'help'])
    except getopt.GetoptError:
        _printArgumentsUsage(); exit(2)
    #end

    global verbose, file_name, flag_EXP_complete, flag_GEN_complete

    # -- you can either define the search object or state here or in the program's arguments:
    searchObject, searchState= None, None

    for opt, arg in opts:
        if opt in ('-v', '--verbose') or opt in ('-v', '--v'):
            print(" -- selected verbose option...")
            verbose = True
        elif opt in ('-fi', '--file'):
            print(" -- provided FOON graph as file '" + str(arg) + "'")
            file_name = arg
        elif opt in ('-ob', '--object'):
            print(" -- given object type '" + str(arg) + "'")
            searchObject = arg
        elif opt in ('-st', '--state'):
            print(" -- given object state '" + str(arg) + "'")
            searchState = ast.literal_eval(arg)
        else:
            _printArgumentsUsage(); exit(2)
        #end
    #endfor

    # -- start by reading the text file:
    start_time = time.time()
    _constructFOON(file_name) 	# -- NOTE: replace text file here with any subgraph/FOON graph file.
    end_time = time.time()
    print(' -- Time taken: ' + (str(end_time - start_time)) + ' s..')

    # -- build internal dictionaries for faster references:
    start_time = time.time()
    _buildInternalMaps()
    end_time = time.time()

    print(' -- Time taken: ' + (str(end_time - start_time)) + ' s..')

    # -- load index files for objects, motions, and states:
    _readIndexFiles()
        
    while True:
        print(); option = _displayMenu(); print()

        # -- based on selection given, perform the following function calls:
        if option == "1":
            print("-- [FOON_MERGE] : Initiating universal FOON merging operation..")
            _mergeSubgraphs()
            new_file_name = _saveFOON_txt()
            if verbose:
                _printSummary_FOON()

            # -- now that we have merged the subgraphs together, we can either work with the new universal FOON or just the loaded file:
            _response = input(' -- Load newly merged FOON or keep using subgraph? (default: 1) [1/2] > ')
            if _response != '2':
                file_name = new_file_name
            _resetFOON(reload=True)
        #end

        elif option == "2":
            # -- call upon other function that will use the retrieval module (FRT):
            _performTreeRetrieval(searchObject, searchState)
        #end

        elif option == "3":
            print(" -- What kind of details do you want to see?")
            print("\t\t1.\tPrint FOON node summary (display total number of object and motion nodes at each level);")
            print("\t\t2.\tPrint FOON functional unit summary (display total number of units at each level);")
            print("\t\t3.\tGenerate label frequency reports (on objects, motions, and states);")
            
            _response = input("  -- Please enter your option or press ENTER to exit : [1-3] > ")
            if _response == "1":
                print("\n -- Printing details about FOON nodes...")
                # -- call upon functions to print summary of number of nodes/edges:
                _printSummary_nodes(); print()
                _printSummary_edges(); print()

                _response = input(" -- Do you want to print the list of nodes? [Y/N] (default:N) > ")
                if _response.lower() == "y":
                    _response = input(" -- At which level? [1/2/3] > ")
                    hierarchy_level = 1 if _response == "1" else 2 if _response == "2" else 3
                    for N in FOON_nodes[hierarchy_level-1]:
                        if isinstance(N, FOON.Object):
                            N.print_functions[hierarchy_level-1]()
                            print("----------------------")
                        #end
                    #end
                #end
            elif _response == "2":
                print("\n -- Printing details about FOON units...")
                # -- call upon functions to print summary of number of functional units in loaded universal FOON:
                _printSummary_FOON(); print()

                _response = input(" -- Do you want to print all functional units? [Y/N] (default:N) > ")
                if _response == "Y" or _response == "y":
                    _response = input(" -- At which level? [1/2/3] > ")
                    hierarchy_level = 1 if _response == "1" else 2 if _response == "2" else 3
                    for N in FOON_functionalUnits[hierarchy_level-1]:
                        N.print_functions[hierarchy_level-1]()
                    #end
                #end
            elif _response == "3":
                print("-- Initiating universal FOON report function..")
                _objectFrequencyReport()
                _motionFrequencyReport()
                _stateFrequencyReport()
            #end
        #end
    
        elif option == "4":
            try:
                import FOON_generalization as fgen
            except ImportError:
                print(" -- ERROR: Missing 'FOON_generalization.py' file!")
                print("\t-- Download here: https://bitbucket.org/davidpaulius/foon_api/src/master/")
                continue
            #endtry

            print(" -- What kind of generalization tasks do you want to do?")
            print("\t\t1.\tPerform network expansion (create a FOON-EXP);")
            print("\t\t2.\tPerform network abstraction (create a FOON-GEN);")
            print("\t\t3.\tPerform task tree retrieval using FOON-EXP;")
            print("\t\t4.\tPerform task tree retrieval using FOON-GEN;")
            print("\t\t5.\tPerform randomized generalization experiment;")
            _response = input("  -- Please enter your option or press ENTER to exit : [1-5] > ")

            print()
            if _response == '1' or _response == '2':
                new_file = _performExpansion() if _response == '1' else _performGeneralization()

                # -- using the newly expanded file, we read it as regular FOON file:
                _response = input('  -- Load expanded/generalized file? [Y/N] (default: N) > ')
                if _response.lower() == 'y':
                    _resetFOON()
                    _constructFOON(new_file)
                    _buildInternalMaps()

            elif _response == "3":

                try:
                    import FOON_retrieval as frt
                except ImportError:
                    print(" -- ERROR: Missing 'FOON_retrieval.py' file!")
                    print('\t-- This module contains the code for all the retrieval operations.')
                    print('\t-- Download here: https://bitbucket.org/davidpaulius/foon_api/src/master/')
                    return None
                            
                if searchObject == None or searchState == None:
                    _response = input(' -- Would you like to look up objects and states by name? [Y/N] (default: N) > ')
                    if _response.lower() == 'y':
                        searchObject, searchState = frt._prepareTaskTreeRetrieval(1)
                    else:
                        searchObject, searchState = frt._prepareTaskTreeRetrieval(2)

                # -- check if expansion has already been done before:
                if not flag_EXP_complete:
                    # -- prepare for expansion by prompting user for parameters to go by (viz. threshold value, method of expansion, etc.)
                    params = fgen._prepareExpansion()
    
                    _response = input(' -- Expand using 1) regular method or 2) text-based method? [1/2] (default: 2) > ')
                    if _response == "1":					
                        expanded_file = fgen._expandNetwork_nontext(
                            object_similarity_index,
                            method=params[0], 
                            threshold=params[1],
                            custom_list=params[2],
                            state_suggestion=params[3]
                        )
                    else:
                        expanded_file = fgen._expandNetwork_text(
                            object_similarity_index, 
                            method=params[0], 
                            threshold=params[1],
                            custom_list=params[2],
                            state_suggestion=params[3]
                        )

                # -- using the newly expanded file, we read it as regular FOON file:
                _constructFOON(expanded_file); _buildInternalMaps()

                _response = input(" -- Would you like to perform: 1) greedy or 2) optimal retrieval? [1/2] > ")
                hierarchy_level = int(input(" -- At what level is the search being done? [1/2/3] > "))
                if _response == "1":
                    frt._taskTreeRetrieval_greedy(searchObject, searchState, hierarchy_level=hierarchy_level)
                elif _response == "2":
                    frt._pathTreeRetrieval(searchObject, searchState, hierarchy_level=hierarchy_level)
                else:
                    pass

                # -- we then restore the FOON to the unexpanded version:
                _resetFOON(reload=True)

            elif _response == "4":
                if not flag_GEN_complete:
                    fgen._constructFOON_GEN() 

                # -- perform task tree retrieval using the abstracted (FOON-GEN) FOON:
                fgen._taskTreeRetrieval_GEN(searchObject, searchState)
            
            elif _response == '5':
                fgen._randomSearchExperiment(
                    n_trials=2,
                    n_objects=5,
                    hierarchy_level=3,
                    expanded_ConceptNet='universal_FOON_27.10.2019_EXP-0.75-Concept-Net-refined.txt',
                    expanded_WordNet='universal_FOON_27.10.2019_EXP-0.87-WordNet-refined.txt'
                )
            #endif

            
        #end

        elif option == "5":
            print("-- [NET-CENT] : Initiating FOON centrality calculation...")
            _response = input(" -- At which level? [1/2/3] > ")
            hierarchy_level = 1 if _response == "1" else 2 if _response == "2" else 3
            _calculateCentrality(hierarchy_level)
        #end

        elif option == '6':
            try:
                import FOON_parser as fpa
            except ImportError:
                print(" -- ERROR: Missing 'FOON_parser.py' script! Please check if it is located in the same directory!")
                print("\t-- Download here: https://bitbucket.org/davidpaulius/foon_api/src/master/")
                continue
            #endtry
            print(' -- [FOON_parser] : Running FOON parsing script...')
            fpa._run_parser()
        #end

        elif option == '7':
            # -- open the user's browser and opens the 'FOON_view' interface:
            print(' -- [FOON_view] : Running FOON graph visualization tool...')
            _startFOONview()
        #end

        elif option == "8":
            print(" -- What kind of file do you want to output?")
            print("\t\t1.\tCreate a .PKL file of the loaded universal FOON;")
            print("\t\t2.\tCreate a .JSON file of the loaded universal FOON;")
            print("\t\t3.\tCreate a .JS (JavaScript) file of the loaded universal FOON;")
            print("\t\t4.\tCreate a .TXT file with FOON word2vec sentences;")
            
            _response = input("  -- Please enter your option or press ENTER to exit : [1-4] > ")

            if _response == "1":
                _saveFOON_pkl()

            elif _response == "2":
                print("-- [FOON_JSON] : Writing FOON graph as .JSON file...")
                _saveFOON_json()

            elif _response == "3":
                print("-- [FOON_JS] : Writing FOON graph as JavaScript file...")
                _saveFOON_JS()
            
            elif _response == "4":
                print("-- Writing FOON functional units as Word2Vec sentences...")
                _FOONtoSentence()
                # _toLSTMSentences()
            #endif
        #end

        # NOTE: Tread ye not below these waters..
        # -- these are debugging or experimental functions that were just there for testing.

        elif option == '13':
            # -- simple function to print any node existing in FOON:
            _object = int(input(' -- Please enter a number corresponding to the node\'s position in list: > '))
            _level = input(' -- At which hierarchy level?: [1/2/3] > ')
            if _level == '':
                _printAnyNode(_object)
            else:
                _printAnyNode(_object, hierarchy_level=int(_level))
        #end
        
        elif option == '14':
            # -- simple function to print a functional unit existing in FOON:
            _object = int(input(' -- Please enter a number corresponding to the functional unit\'s position in list: > '))
            _level = input(' -- At which hierarchy level?: [1/2/3] > ')
            if _level == '':
                _printAnyFunctionalUnit(_object)
            else:
                _printAnyFunctionalUnit(_object, hierarchy_level=int(_level))
        #end
        
        elif option == '55':
            # -- simple function to merge two kitchen files together:
            kitchen_1 = _identifyKitchenItems(input(" -- Enter PATH and FILE NAME of kitchen file #1: > "))
            print("  -- size of kitchen #1 : " + str(len(kitchen_1)))
            kitchen_2 = _identifyKitchenItems(input(" -- Enter PATH and FILE NAME of kitchen file #2: > "))
            print("  -- size of kitchen #2 : " + str(len(kitchen_2)))
            new_kitchen = list(set(kitchen_1 + kitchen_2))
            _file = open('kitchen_merged.txt', 'w')
            for O in new_kitchen:
                text = O.getObjectText()
                if len(text.split('\n')) < 2:
                    print(text)
                _file.write(text); _file.write("\n//\n")
            #endfor
            _file.close()
        #end


        elif option == '':
            print("-- Exiting program", end='')
            for _ in range(5):
                print('.', end=''); time.sleep(0.3)
            print('\n')
            break
        #end
        
        else:
            pass
#enddef

if __name__ == '__main__':
    _start()