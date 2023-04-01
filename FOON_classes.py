'''
FOON_classes (Object Definitions for FOON) 
        (last updated: 15th April, 2022):
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

# NOTE: This file contains the classes needed for the FOON_graph_analyzer.py (FGA) script / program;
#	this will NOT work on its own (unless you plan to implement these classes in another file).
# -- for a general overview of the objects defined in this file, please refer to Paulius et al. 2016 and 2018.

# NOTE: everything is written in an object-oriented style, so please note the definitions below and make changes
#	as you may see fit for your problem area.

# -- set this to True if you are using a recursive ingredients list of actual object nodes:
flag_recursive_objects = False

print_new_style = False

class Thing(object):
    # NOTE: A Thing is a general FOON graph node; it can be either an *object* or a *motion* node.
    # -- Things in FOON have three (3) elements:
    #	1. an identifier (ID) or type, which is an integer;
    #	2. a string label, which tells the user what type of Thing it is;
    #	3. a list of other Things that it is connected to via an edge (i.e. neighbouring nodes).

    # -- constructor methods for creating Thing object:
    def __init__(self, T=None, L=None):
        self.type = T	
        self.label = L 
        self.neighbours = []
    #enddef

    def getType(self):
        return self.type

    def getID(self):
        return self.type

    def getLabel(self):
        return self.label

    def getNeighbourList(self):
        return self.neighbours

    def setType(self, T):
        self.type = T

    def setID(self, T):
        self.type = T

    def setLabel(self, L):
        self.label = L

    def addNeighbour(self, N):
        self.neighbours.append(N)

    def countNeighbours(self):
        return len(self.neighbours)

    def equals(self, T):
        return self.type == T.getType()

    def is_motionNode(self):
        return isinstance(self, Motion)

    def is_objectNode(self):
        return not self.is_motionNode()
#endclass

class Object(Thing):
    # NOTE: -- an Object object is any item that is used in the cooking/manipulation procedure.
    # -- an Object is a Thing inherently, so it must have a type and label as well as a list of its neighbours.
    #	Additionally, an Object has a state type and state label to describe the state or condition it is observed in.
    # -- an Object may have multiple states! This is given by multiple lines of 'S' in the textfiles.

    '''
    A object node object.
    
    Constructor Parameters:
        objectID (int): An integer referring to the object's ID
        objectLabel (str): A string referring to the object's label
        objectPortion (float): A decimal value referring to the object's portion (not used currently)

    '''

    # NOTE: constructor for Object node objects:
    def __init__(self, objectID=None, objectLabel=None, objectPortion=False):
        # -- internal function references:
        self.equals_functions = [self.equals_lvl1, self.equals_lvl2, self.equals_lvl3]
        self.print_functions = [self.printObject_lvl1, self.printObject_lvl2, self.printObject_lvl3]

        super(Object,self).__init__(objectID, objectLabel)

        # -- member variables unique to objects:
        self.objectStates = []
        self.objectIngredients = []
        self.hasPortion = objectPortion
        self.isGoal = False
    #enddef

    # -- accessor methods for Objects:
    def getObjectType(self):
        return super(Object,self).getType()

    def setObjectType(self, N):
        super(Object,self).setType(N)

    def getObjectLabel(self):
        return super(Object,self).getLabel()

    def setObjectLabel(self, L):
        super(Object,self).setLabel(L)

    # NOTE: objects can have multiple states, so we are working with a list of states:
    def getNumberOfStates(self):
        return len(self.objectStates)

    def getStatesList(self):
        return list(self.objectStates)

    def setStatesList(self, S):
        for _state in S:
            self.objectStates.append(list(_state))

    def sortStates(self):
        self.objectStates.sort( key = lambda x: ((x[2] is not None,x[2]), x[0]) )

    def getStateIDs(self):
        _states = []
        for S in self.objectStates:
            _states.append(S[0])
        return _states

    def addNewState(self, T):
        for S in self.objectStates:
            # -- this is to check whether we are potentially adding a duplicate state type or label:
            if S[0] == T[0] and S[1] == T[1] and S[1] and S[2] == T[2]:
                print(' -- WARNING: Duplicate state detected when adding :' + str(T) + ' to object ' + str(self.getObjectLabel()) + '!')
                return
            #endif
        #endfor
        self.objectStates.append(list(T))
        self.sortStates()
    
    def getStateType(self, X):
        return self.objectStates[X][0]

    def getStateLabel(self, X):
        return self.objectStates[X][1]

    def getRelatedObject(self, X):
        # NOTE: not a good name.. but this is supposed to be object label through which this object (self) shares some geometrical property
        # -- signified with square brackets ('[]'); e.g. something is in a bowl -> in <\t> [bowl]
        #	the object is within another object (bowl)
        return self.objectStates[X][2]

    def setRelatedObject(self, X, relatedObj):
        self.objectStates[X][2] = relatedObj

    def getIngredients(self):
        return list(self.objectIngredients)

    def hasIngredients(self):
        return self.objectIngredients

    def setIngredients(self, L):
        self.objectIngredients = list(L)

    def addIngredient(self, I):
        self.objectIngredients.append(I)

    def checkIfGoal(self):
        return self.isGoal

    def setAsGoal(self):
        self.isGoal = True

    # NOTE: Printable functions:
    def getIngredientsText(self, version=2):
        if not flag_recursive_objects or version == 1:
            return self.getIngredientsText_ver_1()
        return self.getIngredientsText_ver_2()
    
    def getIngredientsText_ver_1(self):
        ingredients_list = self.getIngredients(); ingredients = str()

        for x in range(len(ingredients_list)):
            ingredients += ingredients_list[x]
            if x < len(ingredients_list) - 1:
                ingredients += ','
            #endif
        #endfor

        return '{' + ingredients + '}'

    def getIngredientsText_ver_2(self):
        ingredients_list = self.getIngredients()
        if ingredients_list:
            text = '{\n'
            for I in ingredients_list:
                text += '\t\t\t' + str('<ingredient>' + '\n')
                text += '\t\t\t\t' + 'object_id = ' + str(I.getType())  + '\n'
                text += '\t\t\t\t' + "object_label = '" + str(I.getLabel()) + "'\n"
                if I.hasPortion:
                    text += '\t\t\t\t' + 'has_portions = True' + '\n'
                for x in range(len(I.objectStates)):
                    text += '\t\t\t\t' + '<state>' + '\t' + 'state_id = ' + str(I.getStateType(x)) \
                            + '\t' + "state_label = '" + str(I.getStateLabel(x)) + '\t' \
                            + ("relative_object = '" + str(I.getRelatedObject(x) + "'\t") if I.getRelatedObject(x) else '') \
                            + '</state>' + '\n'
                text += '\t\t\t' + '</ingredient>' + '\n'
            #endfor
            return text + '\t\t}'
        #endif
        return '{}'

    def getObjectText(self, motion_descriptor=None, version=2):
        if not print_new_style or version == 1:
            return self.getObjectText_ver1(motion_descriptor=motion_descriptor)
        else:
            return self.getObjectText_ver2(motion_descriptor=motion_descriptor)

    def getObjectText_ver1(self, motion_descriptor=None):
        _text = "O" + str(self.getType()) + '\t' + self.getLabel() + '\t' + str(motion_descriptor)
        for x in range(len(self.objectStates)):
            if 'contains' in self.getStateLabel(x) or 'ingredients' in self.getStateLabel(x):
                _text += "\nS" + str(self.getStateType(x)) + '\t' + self.getStateLabel(x) + '\t' + self.getIngredientsText()
            else:
                _text += "\nS" + str(self.getStateType(x)) + '\t' + self.getStateLabel(x) + (('\t[' + str(self.getRelatedObject(x)) + ']') if self.getRelatedObject(x) else '')
        #endfor
        return _text

    def getObjectText_ver2(self, motion_descriptor=None):
        text = str('<object>' + '\n')
        text += 'object_id = ' + str(self.getType())  + '\n'
        text += "object_label = '" + str(self.getLabel()) + "'\n"
        for x in range(len(self.objectStates)):
            if 'contains' not in self.getStateLabel(x):
                text += '<state>' + '\t' + 'state_id = ' + str(self.getStateType(x)) + \
                    '\t' + "state_label = '" + str(self.getStateLabel(x)) + \
                    '\t' + ("relative_object = '" + str(self.getRelatedObject(x) + "'\t") if self.getRelatedObject(x) else '') + \
                    '</state>' + '\n'
        if self.hasPortion:
            text += 'has_portions = True' + '\n'
        if motion_descriptor:
            text += 'object_in_motion = ' + str(motion_descriptor) + '\n'
        text += 'contains=' + str(self.getIngredientsText()) + '\n'
        text += '</object>' + '\n'
        return text

    # NOTE: this will be used within getFunctionalUnitJSON() method in the FunctionalUnit class below:
    def getObjectJSON(self, motion_descriptor=None, prints_ingredients=False):
        object_as_JSON = {}
        object_as_JSON['object_id'] = self.getType()
        object_as_JSON['object_label'] = str(self.getLabel())
        object_as_JSON['object_states'] = []
        for x in range(len(self.objectStates)):
            state_JSON = {'state_id' : self.getStateType(x), 
                    'state_label' : str(self.getStateLabel(x)) }
            if self.getRelatedObject(x):
                state_JSON['relative_object'] = str(self.getRelatedObject(x))
            object_as_JSON['object_states'].append(state_JSON)
        if not flag_recursive_objects:
            object_as_JSON['ingredients'] = self.getIngredients()
        else:
            object_as_JSON['ingredients'] = []
            for I in self.getIngredients():
                object_as_JSON['ingredients'].append( I.getObjectJSON(), prints_ingredients=True)
        if prints_ingredients == False:
            object_as_JSON['object_in_motion'] = str(motion_descriptor)
            object_as_JSON['has_portions'] = 'True' if self.hasPortion else 'False'		
        return object_as_JSON

    # NOTE: new print functions to make FOON graphs textually more like markup languages:
    # -- these can be switched off using a flag 'flag_recursive_objects' above.

    def printObject_lvl1(self, version=2):
        if not print_new_style or version == 1:
            self.printObject_lvl1_ver1()
        else:
            self.printObject_lvl1_ver2()

    def printObject_lvl1_ver1(self, motion_descriptor=None):
        print("O" + str(self.getObjectType()) + '\t' + self.getObjectLabel() + (('\t' + str(motion_descriptor)) if motion_descriptor else ''))

    def printObject_lvl1_ver2(self, print_FU=False, motion_descriptor=None):
        print( str('\t' if print_FU else '') + '<object>' )
        print( str('\t\t' if print_FU else '\t') + 'object_id = ' + str(self.getType()) )
        print( str('\t\t' if print_FU else '\t') + "object_label = '" + str(self.getLabel()) + "'")
        if self.hasPortion:
            print( str('\t\t' if print_FU else '\t') + 'has_portions = True')		
        if print_FU:
            print( str('\t\t' if print_FU else '\t') + 'object_in_motion = ' + str(motion_descriptor) )
        print( str('\t' if print_FU else '') + '</object>' )

    def printObject_lvl2(self, version=2):
        if not print_new_style or version == 1:
            self.printObject_lvl2_ver1()
        else:
            self.printObject_lvl2_ver2()

    def printObject_lvl2_ver1(self, motion_descriptor=None):
        print("O" + str(self.getObjectType()) + '\t' + self.getObjectLabel() + (('\t' + str(motion_descriptor)) if motion_descriptor else ''))
        for x in range(len(self.getStatesList())):
            print("S" + str(self.getStateType(x)) + '\t' + self.getStateLabel(x) + (('\t[' + str(self.getRelatedObject(x)) + ']') if self.getRelatedObject(x) else ''))
        #endfor
    #end

    def printObject_lvl2_ver2(self, print_FU=False, motion_descriptor=None):
        print( str('\t' if print_FU else '') + '<object>' )
        print( str('\t\t' if print_FU else '\t') + 'object_id = ' + str(self.getType()) )
        print( str('\t\t' if print_FU else '\t') + "object_label = '" + str(self.getLabel()) + "'")
        for x in range(len(self.objectStates)):
            print( str('\t\t' if print_FU else '\t') + '<state>' + '\t' + 
                'state_id =' + str(self.getStateType(x)) + '\t' +
                "state_label = '" + str(self.getStateLabel(x)) + '\t' + 
                ("relative_object = '" + str(self.getRelatedObject(x) + "'\t") if self.getRelatedObject(x) else ' ') + '</state>')
        if self.hasPortion:
            print( str('\t\t' if print_FU else '\t') + 'has_portions = True')		
        if print_FU:
            print( str('\t\t' if print_FU else '\t') + 'object_in_motion = ' + str(motion_descriptor) )
        print( str('\t' if print_FU else '') + '</object>' )

    def printObject_lvl3(self, version=2):
        if not print_new_style or version == 1:
            self.printObject_lvl3_ver1()
        else:
            self.printObject_lvl3_ver2()

    def printObject_lvl3_ver1(self, motion_descriptor=None):
        print("O" + str(self.getObjectType()) + '\t' + self.getObjectLabel() + (('\t' + str(motion_descriptor)) if motion_descriptor else ''))
        for x in range(len(self.getStatesList())):
            if 'contains' in self.getStateLabel(x) or 'ingredients' in self.getStateLabel(x):
                print("S" + str(self.getStateType(x)) + '\t' + self.getStateLabel(x) + '\t' + self.getIngredientsText())
            else:
                print('S' + str(self.getStateType(x)) + '\t' + self.getStateLabel(x) + (str('\t ' + '[' + str(self.getRelatedObject(x)) + ']') if self.getRelatedObject(x) else ''))
        #endfor

    def printObject_lvl3_ver2(self, print_FU=False, motion_descriptor=None):
        print( str('\t' if print_FU else '') + '<object>' )
        print( str('\t\t' if print_FU else '\t') + 'object_id = ' + str(self.getType()) )
        print( str('\t\t' if print_FU else '\t') + "object_label = '" + str(self.getLabel()) + "'")
        for x in range(len(self.objectStates)):
            print( str('\t\t' if print_FU else '\t') + '<state>' + '\t' + 
                'state_id=' + str(self.getStateType(x)) + '\t' + 
                "state_label = '" + str(self.getStateLabel(x)) + "'\t" +
                ("relative_object = '" + str(self.getRelatedObject(x) + "'\t") if self.getRelatedObject(x) else ' ') + '</state>')
        if self.hasPortion:
            print( str('\t\t' if print_FU else '\t') + 'has_portions = True')		
        if print_FU:
            print( str('\t\t' if print_FU else '\t') + 'object_in_motion = ' + str(motion_descriptor) )
        print( str('\t\t' if print_FU else '\t') + 'ingredients = ' + str(self.getIngredientsText()) )
        print( str('\t' if print_FU else '') + '</object>' )

    # NOTE: Comparator methods between objects (levels 1 thru 3):
    def isSameStates(self, O):
        # -- first, sort the lists for fair comparison:
        self.sortStates(); O.sortStates()

        # -- set counter used to record number of matching states:
        count = 0
        for S in self.objectStates:
            for SU in O.objectStates:
                if S[0] == SU[0] and S[1] == SU[1] and S[2] == SU[2]:
                    count += 1

        if count == len(O.objectStates) and len(self.objectStates) == len(O.objectStates):
            return True
        return False

    def isSameStates_ID_only(self, O):
        # -- first, sort the lists for fair comparison:
        self.sortStates(); O.sortStates()

        # -- set counter used to record number of matching states:
        count = 0
        for S in self.objectStates:
            for SU in O.objectStates:
                if S[0] == SU[0]:
                    count += 1

        if count == len(O.objectStates) and len(self.objectStates) == len(O.objectStates):
            return True
        return False

    def isSameIngredients(self, O):
        if len(self.objectIngredients) != len(O.objectIngredients):
            return False
        
        # -- sort list of ingredients:
        O.objectIngredients.sort()
        self.objectIngredients.sort()

        # -- set counter to 0, and if counter == len(self.ingredients), return true:
        count = 0
        for x in range(len(O.objectIngredients)):
            if O.objectIngredients[x] in self.objectIngredients:
                count += 1

        return count == len(self.objectIngredients)

    def equals_lvl1(self, O):
        return self.getObjectType() == O.getObjectType()

    def equals_lvl2(self, O):
        return self.equals_lvl1(O) and self.isSameStates(O) 

    def equals_lvl3(self, O):
        return self.equals_lvl2(O) and self.isSameIngredients(O)

    def getObjectKey(self, H=3):
        if H == 1:
            return 'O' + str(self.getType())
        elif H == 2:
            _string = ''
            for x in range(len(self.getStatesList())):
                _string += 'S' + str(self.getStateType(x)) + str('_' + (str(self.getRelatedObject(x)) if self.getRelatedObject(x) else '') )
            return 'O' + str(self.getObjectType()) + _string
        elif H == 3:
            _string = ''
            for x in range(len(self.getStatesList())):
                _string += 'S' + str(self.getStateType(x)) + str('_' + (str(self.getRelatedObject(x)) if self.getRelatedObject(x) else '') )
            return 'O' + str(self.getObjectType()) + _string + self.getIngredientsText().replace(' ', '_')
        else:
            pass

#endclass

class Motion(Thing):
    # NOTE: -- a Motion node is the other node that is found in the bipartite FOON graph.
    # -- a Motion node reflects a manipulation or non-manipulation action that is needed to change (some) objects from one state to another
    # -- a Motion node simply has a type that describes what it is along with a label.

    '''
    A motion node object.
    
    Constructor Parameters:
        motionID (int): An integer referring to the motion's ID
        motionLabel (str): A string referring to the motion's label
        motionCode (str): A string referring to the motion code that best describes this motion (refer to Paulius et al. 2019, 2020 on motion taxonomy)

    '''

    # NOTE: constructor method for Motion node objects:
    def __init__(self, motionID=None, motionLabel=None, motionCode=None):
        # -- use super-class (Thing) methods:
        super(Motion,self).__init__(motionID, motionLabel)
        # -- motion code refers to the taxonomy coding (currently not incorporated in FOON):
        self.motionCode = str(motionCode) if motionCode else None

    def getMotionType(self):
        return super(Motion,self).getType()

    def setMotionType(self, M):
        super(Motion,self).setType(M)

    def getMotionLabel(self):
        return super(Motion,self).getLabel()

    def setMotionLabel(self, M):
        super(Motion,self).setLabel(M)

    def equals(self, M):
        return self.getMotionType() == M.getMotionType()

    def printMotion(self):
        print('<motion>')
        print('\t' + 'motion_id = ' + str(self.getMotionType()) )
        print('\t' + "motion_label = '" + self.getMotionLabel() + "'")
        print('</motion>')

    def getMotionText(self):
        text = '\t' + 'motion_id = ' + str(self.getMotionType()) + '\n' 
        text += '\t' + "motion_label = '" + self.getMotionLabel() + "'\n"
        return text

    def getMotionJSON(self):
        motion_as_JSON = {}
        motion_as_JSON['motion_id'] = str(self.getMotionType()) 
        motion_as_JSON['motion_label'] = self.getMotionLabel()
        motion_as_JSON['robot_type'] = None
        motion_as_JSON['weight_success'] = None
        return motion_as_JSON
#endclass

class FunctionalUnit(object):
    def __init__(self):
        # NOTE: list of input and output object nodes (which use the Object class defined above):
        self.inputNodes = []; self.outputNodes = []

        # NOTE: list of object motion identifiers for each object node (since this is based on the functional unit more than the objects themselves)
        self.inDescriptor = []; self.outDescriptor = []

        self.times = [None, None]	# NOTE: the start and end times for a functional unit occurring in a sequence (irrelevant for universal FOON)
        self.motionNode = None	# NOTE: motion node that belongs to a functional unit instance
        self.success_rate = None	# NOTE: success rate for a functional unit's execution (please refer to Paulius et al. 2019 for more info)
        self.entity = ''		# NOTE: entity reflects if the success rate pertains to robot or human

        # -- link to functions for easy calling with respect to a certain level:
        self.equals_functions = [self.equals_lvl1, self.equals_lvl2, self.equals_lvl3]
        self.print_functions = [self.printFunctionalUnit_lvl1, self.printFunctionalUnit_lvl2, self.printFunctionalUnit_lvl3]
    #enddef

    # -- overriding definitions of comparator functions:
    def __lt__(self, O):
        if self.success_rate and O.success_rate:
            return self.success_rate < O.success_rate
        return False

    def __gt__(self, O):
        if self.success_rate and O.success_rate:
            return self.success_rate > O.success_rate
        return False

    def isEmpty(self):
        # -- quite simply, a functional unit is empty if it has no Motion node or no Input/Output nodes:
        return not self.motionNode or not self.inputNodes or not self.outputNodes

    def addObjectNode(self, objectNode, is_input, is_active_motion):
        # NOTE: is_active_motion :- signifies if the object is actively moving (1) or passively / not moving (0)
        #               -- refer to motion taxonomy / motion code works by Paulius et al. 2020, Alibayev et al. 2021

        # NOTE: is_input :- if true, object is added to input node list; else, it is added to object output list.

        if is_input:
            if objectNode not in self.inputNodes:
                self.inputNodes.append(objectNode); self.inDescriptor.append(is_active_motion)
        else:
            if objectNode not in self.outputNodes:
                self.outputNodes.append(objectNode); self.outDescriptor.append(is_active_motion)
        #endif
    #enddef

    def equals_lvl3(self, U):
        results = 0 	# -- this number must add up to three (3) which suggests that all parts match!
        count = 0		# -- counter used to determine number of hits (true matches)

        # 1. Check if the input nodes are all the same:
        for T in self.inputNodes:
            for TU in U.inputNodes:
                if T.equals_lvl3(TU):
                    count = count + 1

        # -- if the counter matches up to the number of inputs,
        #		then that means we have the same set of inputs.
        if count == self.getNumberOfInputs() and self.getNumberOfInputs() == U.getNumberOfInputs():
            results = results + 1

        # 2. Check if the Motion is the same
        if self.motionNode.equals(U.motionNode):
            results = results + 1

        # 3. Check if the output nodes are all the same:
        count = 0
        for T in self.outputNodes:
            for TU in U.outputNodes:
                if T.equals_lvl3(TU):
                    count = count + 1

        # -- if the counter matches up to the number of inputs,
        #		then that means we have the same set of inputs.
        if count == self.getNumberOfOutputs() and self.getNumberOfOutputs() == U.getNumberOfOutputs():
            results = results + 1

        # -- simply return true or false depending on the value of results
        return results == 3
    #enddef

    def equals_lvl2(self, U):
        results = 0 	# -- this number must add up to three (3) which suggests that all parts match!
        count = 0		# -- counter used to determine number of hits (true matches)

        # 1. Check if the input nodes are all the same:
        for T in self.inputNodes:
            for TU in U.inputNodes:
                if T.equals_lvl2(TU):
                    count = count + 1

        # -- if the counter matches up to the number of inputs,
        #		then that means we have the same set of inputs.
        if count == self.getNumberOfInputs() and self.getNumberOfInputs() == U.getNumberOfInputs():
            results = results + 1

        # 2. Check if the Motion is the same
        if self.motionNode.equals(U.motionNode):
            results = results + 1

        # 3. Check if the output nodes are all the same:
        count = 0
        for T in self.outputNodes:
            for TU in U.outputNodes:
                if T.equals_lvl2(TU):
                    count = count + 1

        # -- if the counter matches up to the number of inputs,
        #		then that means we have the same set of inputs.
        if count == self.getNumberOfOutputs() and self.getNumberOfOutputs() == U.getNumberOfOutputs():
            results = results + 1

        # -- simply return true or false depending on the value of results
        return results == 3
    #enddef

    def equals_lvl1(self, U):
        results = 0 	# -- this number must add up to three (3) which suggests that all parts match!
        count = 0		# -- counter used to determine number of hits (true matches)

        # 1. Check if the input nodes are all the same:
        for T in self.inputNodes:
            for TU in U.inputNodes:
                if T.equals_lvl1(TU):
                    count = count + 1

        # -- if the counter matches up to the number of inputs,
        #		then that means we have the same set of inputs.
        if count == self.getNumberOfInputs() and self.getNumberOfInputs() == U.getNumberOfInputs():
            results = results + 1

        # 2. Check if the Motion is the same
        if self.motionNode.equals(U.motionNode):
            results = results + 1

        # 3. Check if the output nodes are all the same:
        count = 0
        for T in self.outputNodes:
            for TU in U.outputNodes:
                if T.equals_lvl1(TU):
                    count = count + 1

        # -- if the counter matches up to the number of inputs,
        #		then that means we have the same set of inputs.
        if count == self.getNumberOfOutputs() and self.getNumberOfOutputs() == U.getNumberOfOutputs():
            results = results + 1

        # -- simply return true or false depending on the value of results
        return results == 3
    #enddef

    def getMotion(self):
        return self.motionNode

    def setMotion(self, M):
        self.motionNode = M

    def getMotionNode(self):
        return self.motionNode

    def setMotionNode(self, M):
        self.motionNode = M

    def getInputList(self):
        return self.inputNodes

    def getOutputList(self):
        return self.outputNodes

    def getInputNodes(self):
        return self.getInputList()

    def getOutputNodes(self):
        return self.getOutputList()

    def setInputList(self, L):
        self.inputNodes = L

    def setOutputList(self, L):
        self.outputNodes = L

    def getNumberOfInputs(self):
        return len(self.inputNodes)

    def getNumberOfOutputs(self):
        return len(self.outputNodes)

    # NOTE: motion descriptor is the integer in a functional unit describing if an object is in motion 
    # 	(typically active motion - refer to our work on "motion taxonomy"):
    def getInputDescriptor(self, X=None):
        return self.inDescriptor if X is None else self.inDescriptor[X]

    def getOutputDescriptor(self, X=None):
        return self.outDescriptor if X is None else self.outDescriptor[X]

    def getMotionDescriptor(self, X, is_input=True):
        if is_input:
            return self.inDescriptor[X]
        return self.outDescriptor[X]

    def setTimes(self, S, E):
        if S != 'Assumed' or E != 'Assumed':
            self.times = [S, E]

    def getStartTime(self):
        return self.times[0]

    def getEndTime(self):
        return self.times[1]

    def hasValidTimes(self):
        return self.times[0] and self.times[1]

    def setIndication(self, ID):
        self.entity = ID

    def getIndication(self):
        return self.entity

    def setSuccessRate(self, SR):
        self.success_rate = SR

    def getSuccessRate(self):
        return self.success_rate

    def printMotion(self, version=2):
        if not print_new_style or version == 1:
            self.printMotion_ver1()
        else:
            self.printMotion_ver2()

    def printMotion_ver1(self):
        text = 'M' + str(self.motionNode.getMotionType())  + '\t' + self.motionNode.getMotionLabel() + '\t' + \
            ( str('<' + str(self.times[0]) + ',' + str(self.times[1]) + '>') if (self.times[0] and self.times[1]) else '<Assumed>')
        if self.success_rate:
            text += '\t' + self.entity + '\t' + str(self.success_rate)
        print(text)

    def printMotion_ver2(self):
        print('<motion>')
        print(self.motionNode.getMotionText(), end='')

        if self.times[0] and self.times[1]:
            print('\t' + 'start_time =\t' + self.times[0])
            print('\t' + 'end_time =\t' + self.times[1] )
        else:
            print('\t' + 'start_time =\tAssumed')
            print('\t' + 'end_time =\tAssumed')

        if self.success_rate:
            print('\t' + 'weight_success = ' + str(self.success_rate))

        print('</motion>')

    def printFunctionalUnit_lvl1(self, version=1):
        if not print_new_style or version == 1:
            self.printFunctionalUnit_lvl1_ver1()
        else:
            self.printFunctionalUnit_lvl1_ver2()

    def printFunctionalUnit_lvl1_ver1(self):
        for T in self.inputNodes:
            T.printObject_lvl1_ver1(motion_descriptor=str(self.inDescriptor[self.inputNodes.index(T)]) )
        #endfor

        self.printMotion()

        for T in self.outputNodes:
            T.printObject_lvl2_ver1(motion_descriptor=str(self.outDescriptor[self.outputNodes.index(T)]) )
        #endfor

        if self.success_rate:
            print("success rate for Robot: " + str(self.success_rate))
    #enddef

    def printFunctionalUnit_lvl1_ver2(self):
        print('<input_nodes>')
        for T in self.inputNodes:
            T.printObject_lvl1(print_FU=True, motion_descriptor=str(self.inDescriptor[self.inputNodes.index(T)]) )
        print('</input_nodes>')

        self.printMotion()

        print('<output_nodes>')
        for T in self.outputNodes:
            T.printObject_lvl1(print_FU=True, motion_descriptor=str(self.outDescriptor[self.outputNodes.index(T)]) )
        print('</output_nodes>')
    #enddef
    
    def printFunctionalUnit_lvl2(self, version=1):
        if not print_new_style or version == 1:
            self.printFunctionalUnit_lvl2_ver1()
        else:
            self.printFunctionalUnit_lvl2_ver2()

    def printFunctionalUnit_lvl2_ver1(self):
        for T in self.inputNodes:
            T.printObject_lvl2_ver1(motion_descriptor=str(self.inDescriptor[self.inputNodes.index(T)]) )
        #endfor

        self.printMotion()

        for T in self.outputNodes:
            T.printObject_lvl2_ver1(motion_descriptor=str(self.outDescriptor[self.outputNodes.index(T)]) )
        #endfor

        if self.success_rate:
            print("success rate for Robot: " + str(self.success_rate))
    #enddef

    def printFunctionalUnit_lvl2_ver2(self):
        print('<input_nodes>')
        for T in self.inputNodes:
            T.printObject_lvl2(print_FU=True, motion_descriptor=str(self.inDescriptor[self.inputNodes.index(T)]) )
        print('</input_nodes>')

        self.printMotion()

        print('<output_nodes>')
        for T in self.outputNodes:
            T.printObject_lvl2(print_FU=True, motion_descriptor=str(self.outDescriptor[self.outputNodes.index(T)]) )
        print('</output_nodes>')
    #enddef

    def printFunctionalUnit_lvl3(self, version=1):
        if not print_new_style or version == 1:
            self.printFunctionalUnit_lvl3_ver1()
        else:
            self.printFunctionalUnit_lvl3_ver2()
    
    def printFunctionalUnit_lvl3_ver1(self):
        for T in self.inputNodes:
            T.printObject_lvl3_ver1(motion_descriptor=str(self.inDescriptor[self.inputNodes.index(T)]) )
        #endfor

        self.printMotion()

        for T in self.outputNodes:
            T.printObject_lvl3_ver1(motion_descriptor=str(self.outDescriptor[self.outputNodes.index(T)]) )
        #endfor

        if self.success_rate:
            print("success rate for Robot: " + str(self.success_rate))

    def printFunctionalUnit_lvl3_ver2(self):
        print('<input_nodes>')
        for T in self.inputNodes:
            T.printObject_lvl3(print_FU=True, motion_descriptor=str(self.inDescriptor[self.inputNodes.index(T)]) )
        print('</input_nodes>')

        self.printMotion()

        print('<output_nodes>')
        for T in self.outputNodes:
            T.printObject_lvl3(print_FU=True, motion_descriptor=str(self.outDescriptor[self.outputNodes.index(T)]) )
        print('</output_nodes>')
    #enddef

    def getInputsForFile(self):
        cat = str()
        for T in self.inputNodes:
            cat += T.getObjectText( motion_descriptor=self.inDescriptor[self.inputNodes.index(T)], version=1 ) + '\n'
        return cat

    def getOutputsForFile(self):
        cat = str()
        for T in self.outputNodes:
            cat += T.getObjectText( motion_descriptor=self.outDescriptor[self.outputNodes.index(T)], version=1 ) + '\n'
        return cat

    def getInputNodeText(self, x):
        return self.inputNodes[x].getObjectText( motion_descriptor=self.inDescriptor[x], version=1 ) + '\n'

    def getOutputNodeText(self, x):
        return self.outputNodes[x].getObjectText( motion_descriptor=self.outDescriptor[x], version=1 ) + '\n'

    def getMotionForFile(self):
        _string = "M" + str(self.motionNode.getMotionType()) + '\t' + self.motionNode.getMotionLabel() + '\t' + \
            ( str('<' + str(self.times[0]) + ',' + str(self.times[1]) + '>') if (self.times[0] and self.times[1]) else '<Assumed>')
        if self.success_rate and self.success_rate > 0:
            _string += '\t' + self.entity + '\t' + str(self.success_rate)
        return _string + "\n"

    def getWord2VecSentence(self):
        sentence = ''
        for _input in self.inputNodes:
            sentence += _input.getObjectLabel().replace(' ', '_') + ' '
        sentence += self.motionNode.getMotionLabel().replace(' ', '_') + ' '
        for _output in self.outputNodes:
            sentence += _output.getObjectLabel().replace(' ', '_') + ' '
        return sentence

    def getFunctionalUnitJSON(self):
        # NOTE: function used to return functional units for a JSON file:
        func_unit_as_JSON = { 'input_nodes' : [], 'motion_node' : None, 'output_nodes' : [] }

        for N in self.inputNodes:
            object_as_JSON = N.getObjectJSON( motion_descriptor=self.inDescriptor[self.inputNodes.index(N)] )
            func_unit_as_JSON['input_nodes'].append(object_as_JSON)
        
        motion_as_JSON = self.motionNode.getMotionJSON()
        motion_as_JSON['start_time'] = self.times[0] if self.times[0] else 'Assumed'
        motion_as_JSON['end_time'] = self.times[1] if self.times[1] else 'Assumed'

        # -- only add weights and robot type if it is available to the functional unit:
        if self.entity:
            motion_as_JSON['robot_type'] = self.entity
        else:
            motion_as_JSON.pop('robot_type', None)
        if self.success_rate:
            motion_as_JSON['weight_success'] = self.success_rate
        else:
            motion_as_JSON.pop('weight_success', None)

        func_unit_as_JSON['motion_node'] = motion_as_JSON

        for N in self.outputNodes:
            object_as_JSON = N.getObjectJSON( motion_descriptor=self.outDescriptor[self.outputNodes.index(N)] )
            func_unit_as_JSON['output_nodes'].append(object_as_JSON)

        return func_unit_as_JSON

    def getFunctionalUnitText(self):
        return self.getInputsForFile() + self.getMotionForFile() + self.getOutputsForFile() + '//\n'

    # NOTE: functions to check if a certain object exists in a functional unit:
    def inputExists(self, I):
        for T in self.inputNodes:
            if I.equals(T):
                 return True
        return False

    def outputExists(self, I):
        for T in self.outputNodes:
            if I.equals(T):
                 return True
        return False

    def containsInput(self, O):
        for N in self.inputNodes:
            if N.getObjectType() == O.getObjectType() or N.getObjectLabel() == O.getObjectLabel():
                return True
        return False

    def containsOutput(self, O):
        for N in self.outputNodes:
            if N.getObjectType() == O.getObjectType() or N.getObjectLabel() == O.getObjectLabel():
                return True
        return False

    def containsObject(self, O):
        return self.containsInput(O) or self.containsOutput(O)

    def copyFunctionalUnit(self):
        functional_unit_copy = FunctionalUnit()
        
        # -- copying input nodes:
        for x in range(len(self.inputNodes)):
            original_object = self.inputNodes[x]
            
            # -- create new object node instance:
            object_copy = Object( objectID=original_object.getObjectType(), objectLabel=original_object.getObjectLabel() )
            object_copy.setIngredients( list(original_object.getIngredients()) )
            object_copy.setStatesList( original_object.getStatesList() )

            functional_unit_copy.addObjectNode(object_copy, True, self.inDescriptor[x])
        #endif

        # -- copying output nodes:
        for x in range(len(self.outputNodes)):
            original_object = self.outputNodes[x]
            
            # -- create new object node instance:
            object_copy = Object( objectID=original_object.getObjectType(), objectLabel=original_object.getObjectLabel() )
            object_copy.setIngredients( list(original_object.getIngredients()) )
            object_copy.setStatesList( original_object.getStatesList() )

            functional_unit_copy.addObjectNode(object_copy, False, self.outDescriptor[x])
        #endif

        # -- copying and set motion node information:
        motion_copy = Motion(motionID=self.getMotionNode().getMotionType(), motionLabel=self.getMotionNode().getMotionLabel())
        functional_unit_copy.setMotion(motion_copy)
        functional_unit_copy.setTimes(self.getStartTime(), self.getEndTime())

        return functional_unit_copy
    #enddef

#endclass

# NOTE: Category objects are used for the generalization of FOON objects:
class Category(object):
    def __init__(self, S=None, I=None):
        self.category_label = S; self.category_ID = I

    def setLabel(self, S):
        self.category_label = S

    def setID(self, I):
        self.category_ID = I
        
    def getLabel(self):
        return self.category_label

    def getID(self):
        return self.category_ID

    def printCategory(self):
        print('O' + str(self.category_ID) + '\t' + str(self.category_label))
#encclass

class TreeNode(object):
    # NOTE: TreeNode object is used for the path tree retrieval function.
    # -- this is used when determining the optimal path for task planning (based on success rates) or to find all possible combinations of units:

    # NOTE: constructor method for TreeNode object:
    def __init__(self):
        # -- all functional units are referred to based on their index value (to make it less intensive on memory):
        self.parents = []		# -- points to any TreeNode objects that precede it
        self.children = []		# -- points to any TreeNode that follows it
        self.ancestors = set()		# -- lists all FUs that were seen above this node
        self.units_contained = []	# -- lists all FUs that make up a particular dependency node
        self.level = 0		# -- keeping track of the level of depth in the TreeNode tree
        self.items_seen = set()

    # -- redefinition of equals and ~equals functions:
    def __eq__(self, other):
        return (self.__class__ == other.__class__) and (set(self.units_contained) == set(other.units_contained))

    def __ne__(self, other):
        return (self.__class__ != other.__class__) or (set(self.units_contained) != set(other.units_contained))

    def __hash__(self):
        return hash(tuple(set(self.units_contained)))

    def __str__(self):
        return str(self.units_contained)

    def getChildren(self):
        return self.children

    def setChildren(self, L):
        '''
        Function to set a TreeNode's children to its correct node.
        '''		
        self.children = L

    def addChild(self, L):
        self.children.append(L)

    def getParents(self):
        return self.parents

    def setParents(self, P):
        self.parents = P

    def addParent(self, P):
        self.parents.append(P)

    def getUnitsInTreeNode(self):
        '''
        Function to get a TreeNode's functional units ()
        '''		
        return self.units_contained

    def setUnitsToTreeNode(self, L):
        self.units_contained = L

    def getLevel(self):
        return self.level

    def setLevel(self, L):
        self.level = L

    def setAncestors(self, A):
        self.ancestors = A

    def getAncestors(self):
        return self.ancestors

    def isInAncestors(self, F):
        if F in self.ancestors:
            return True
        return False
    #enddef

    def setItemsSeen(self, A):
        self.items_seen = A

    def getItemsSeen(self):
        return self.items_seen

    def isAlreadySeen(self, F):
        if F in self.items_seen:
            return True
        return False
    #enddef

    def printTreeNode(self, FOON, hierarchy_level=3):
        print('~~~*')
        for FU in self.units_contained:
            FOON[FU].print_functions[hierarchy_level-1]()
        print('~~~')

    # -- function to return a list of all paths from a given root node:
    # 	SOURCE: https://stackoverflow.com/questions/25840327/how-to-return-all-possible-paths-of-random-binary-tree-in-python
    @staticmethod
    def makeList(tree, level=0):
        paths = []
        if not tree.children:
            P = []
            for A in tree.units_contained:
                P.append(A)
            return [P]
        for C in tree.children:
            P = []
            for A in tree.units_contained:
                P.append(A)
            paths.extend([P + child for child in TreeNode.makeList(C, level+1)])
        return paths
    #enddef

    @staticmethod
    def printPathTree(tree):
        import collections

        # -- we use a queue to maintain order of traversal:
        print('|-root_lvl' + str(tree.level) +  '=[' + str(tree.units_contained) + ']')
        queue = collections.deque()
        for C in tree.children:
            queue.append(C)

        # -- print everything using in-order traversal:
        while queue:
            tree_node = queue.popleft()
            print( str('  ' * tree_node.level) + '|-child_lvl' + str(tree_node.level) + '=[' + str(tree_node.units_contained) + ']')
            for C in tree_node.children:
                queue.appendleft(C)
        #endwhile
    #end

#endclass