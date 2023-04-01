'''
FOON: Generalization Methods (FOON_generalization):
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
import FOON_classes as FOON

import collections, time, tqdm, os, getopt, sys

# -- write timestamp of when file was created for record-keeping:
from datetime import datetime

last_updated = '21st April, 2022'

# -- verbose flag to print any extra comments or prompts for debugging:
verbose = False

file_name = None

# NOTE: this dictionary is used to store the similarity value between pairs of objects:
object_similarity_index = {}

# NOTE: storing the sense id for objects (based on WordNet) or to denote Concept-Net sense -- these were verified semi-automatically using parser!
FOON_objectSenses = {}

# NOTE: the following are dictionaries used for mapping categories to object labels (for generalization of FOON):
FOON_objectClusters = {}; FOON_objectCluster_index = {}

# NOTE: these lists are used for the generalization of FOON:
# -- Two "generalized" versions of FOON:
# 	1. FOON-EXP - expanded version of FOON that uses WordNet/Concept-Net similarities to create new units;
#		-- this would use the regular FOON lists from above since we perform expansion and read the new file created
# 	2. FOON-GEN - compressed version of FOON that uses object categories
# -- please refer to Paulius et al. 2018 for more explanation on these approaches.
FOON_functionalUnits_compressed = []; FOON_nodes_compressed = []; FOON_outputsToUnits_compressed = {}

# -- is_expansion_done :- flag to indicate whether expansion has already been applied to the loaded FOON graph:
is_expansion_done = False

# -- is_compression_done :- flag to indicate whether compression has already been applied to the loaded FOON graph:
is_compression_done = False

# -- copies of dictionaries from FGA (FOON Graph Analyzer):
FOON_functionalUnits, FOON_nodes, FOON_outputsToUnits, FOON_objectsToUnits, FOON_functionalUnitMap = None, None, None, None, None
FOON_objectLabels, FOON_motionLabels, FOON_stateLabels = {}, {}, {}

# -- references to the word embedding models that will be loaded and possibly re-used:
w2v_conceptnet = None
spacy_model = None

expansion_threshold, expansion_model = None, None


def _copyDicts(data):
    # NOTE: in Python, global variables are only global within the scope of a module (i.e., file);
    # 	therefore, this function is used to bypass that by copying references from FGA for the necessary
    #       lists or dictionaries for search.

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

    # -- getting object senses (if needed for WordNet or Concept-Net):
    global FOON_objectSenses
    if 'obj_senses' in data:
        FOON_objectSenses = data['obj_senses']

    global file_name
    if 'FOON_file_name' in data:
        file_name = data['FOON_file_name']

#enddef


def _startGeneralization(args):
    if args['method'] == 1:
        # -- perform expansion:
        expanded_file = _expandNetwork_text()
        return expanded_file
    else:
        # -- perform compression:
        compressed_file = _compressNetwork()
        return compressed_file
#enddef


def _load_conceptnet_model():
    global path_to_ConceptNet, w2v_conceptnet

    # -- check if a path has already been specified during run-time:
    if not path_to_ConceptNet:
        path_to_ConceptNet = input('  -- Enter the full path and name to the Concept-Net model file: > ')

    # NOTE: we need to use gensim to load the numberbatch file:
    try:
        from gensim.models import KeyedVectors
    except ImportError:
        print(' -- ERROR: Missing gensim library!')
        print("\t-- Please install gensim using 'pip install gensim' in terminal.")
        print("\t-- Refer to https://radimrehurek.com/gensim/install.html for more details!")
        return

    # -- load word embeddings for Concept-Net:
    try:
        w2v_conceptnet = KeyedVectors.load_word2vec_format(path_to_ConceptNet, binary=True)
    except:
        print(' -- ERROR: Problem loading word2vec model file!')
        print('\t-- Please download it here and try again: https://github.com/commonsense/Concept-Net-numberbatch')
    #endtry
#enddef


def _load_spacy_model():
    global spacy_model

    try:
        import spacy
    except ImportError:
        print(' -- ERROR: Missing spaCy library!')
        print("\t-- Please install spacy with the instructions here: https://spacy.io/usage")
        exit()

    try:
        #spacy_model = spacy.load("en_core_web_lg")
        spacy_model = spacy.load("en_core_web_lg", disable=["tagger", "parser"])
    except:
        print(' -- ERROR: Problem loading word2vec model file!')
        print("\t-- Please download the model via 'python -m spacy download en_core_web_lg' (according to https://spacy.io/usage)")
        exit()
    #endtry
#enddef


def _computeSimilarity(X, Y, method='spacy'):

    # NOTE: this function is used to compute similarity between two words represented as X and Y;
    #   the idea of similarity is to find out if a word pair can be interchanged for FOON.

    # -- there are different models or databases that are used to measure similarity:
    #   1. WordNet - classical, hierarchical, lexical dataset, where words are explicitly categorized in a tree-like structure.
    #   2. Concept-Net - embedded representation of words and relation types from crawling the web (iirc) as a word embedding model
    #   3. SpaCy - large scale, industrial NLP toolkit with pre-trained word embedding models

    global FOON_objectLabels

    def _computeSimilarity_wordnet():

        # -- by default, we will assign a value of 0
        sim_value = 0.0

        # NOTE: this operation requires WordNet, which is available through NLTK.
        # -- Read more about this here: http://www.nltk.org/howto/wordnet.html
        try:
            from nltk.corpus import wordnet as wn
            from nltk.corpus.reader.wordnet import WordNetError

        except ImportError:
            print(" -- ERROR: Missing NLTK library and/or WordNet corpus! Cannot build object similarity index!")
            print("\t-- Please install it using 'pip install nltk' and then use 'nltk.download()'!")
            print("\t-- Refer to https://www.nltk.org/data.html for more details!")
            return

        # -- this requires definition of senses as used in WordNet:
        global FOON_objectSenses

        # -- if two words have the same object ID (due to being synonyms, aliases, instances, etc.), 
        #	then we can say that they are exact matches
        if FOON_objectLabels[X] == FOON_objectLabels[Y]:
            sim_value = 1.0
    
        else:
            try:
                if verbose:
                    print(" -- Comparing '" + str(X) + "' with '" + str(Y) + "'...")

                # -- creating word objects with the name of the items using NLTK

                # NOTE: here, we need to directly indicate WHICH synset definition (sense) should be used for certain words, 
                # 	as the first sense is not always food-related. These are manually identified and placed in FOON-object_index.txt file.
                word_1 = wn.synset(str(X.replace(' ', '_')) + '.n.0' + str(FOON_objectSenses[X]))
                word_2 = wn.synset(str(Y.replace(' ', '_')) + '.n.0' + str(FOON_objectSenses[Y]))

                # -- calculate Wu-Palmer metric for the words (for ALL senses);
                #	Wu-Palmer is typically used, but other metrics can be used (check NLTK documentation!)
                sim_value = word_1.wup_similarity(word_2)

            except WordNetError or KeyError:
                # NOTE: WordNetError means that the object is not found in WordNet
                pass
            
            #endtry
        #endif
        return sim_value
    #enddef

    def _computeSimilarity_conceptnet():
        # NOTE: we will use the numberbatch/word2vec model for Concept-Net, 
        # 	which can be downloaded here: https://github.com/commonsense/Concept-Net-numberbatch

        global w2v_conceptnet

        sim_value = 0

        # -- check if the model has not been loaded into memory (only do this once):
        if not w2v_conceptnet:
            _load_conceptnet_model()

        # -- if two words have the same object ID (due to being synonyms, aliases, instances, etc.), 
        #	then we can say that they are exact matches
        if FOON_objectLabels[X] == FOON_objectLabels[Y]:
            sim_value = 1.0
    
        else:
            try:
                if verbose:
                    print(" -- Comparing '" + str(X) + "' with '" + str(Y) + "'...")

                # -- need to replace whitespaces with underscores:
                word_1 = X.replace(' ', '_'); word_2 = Y.replace(' ', '_')

                # NOTE: use gensim's similarity method (in KeyedVectors class) to calculate relatedness:
                sim_value = w2v_conceptnet.similarity(str(word_1), str(word_2))

            except KeyError:
                # NOTE: this means that one of the words or expressions was not in Word2Vec:
                pass
        #endif

        return sim_value
    #enddef

    def _computeSimilarity_spacy():
        # NOTE: we will use the word embedding model provided by the spaCy library, 
        # 	which can be downloaded here: https://spacy.io/usage

        global spacy_model

        # -- check if the model has not been loaded into memory (only do this once):
        if not spacy_model:
            _load_spacy_model()

        # -- if two words have the same object ID (due to being synonyms, aliases, instances, etc.), 
        #	then we can say that they are exact matches
        if FOON_objectLabels[X] == FOON_objectLabels[Y]:
            sim_value = 1.0
    
        else:
            try:
                if verbose:
                    print(" -- Comparing '" + str(X) + "' with '" + str(Y) + "'...")

                # -- need to replace whitespaces with underscores:
                word_1 = spacy_model(X.replace(' ', '_'))
                word_2 = spacy_model(Y.replace(' ', '_'))

                if word_1.has_vector is False or word_2.has_vector is False:
                    # -- if a word does not have an embedded representation, then just give value of 0:
                    sim_value = 0
                else:
                    # NOTE: use spacy's similarity method to calculate relatedness:
                    sim_value = word_1.similarity(word_2)
                #endif
            except KeyError:
                # NOTE: this means that one of the words or expressions was not in Word2Vec:
                pass
        #endif

        return sim_value
    #enddef

    if method == 'WordNet':
        similarity_value = _computeSimilarity_wordnet()
    elif method == 'ConceptNet':
        similarity_value = _computeSimilarity_conceptnet()
    else:
        similarity_value = _computeSimilarity_spacy()
    #endif

    return similarity_value
#enddef


def _findObjectSubstitute(O, method="spacy", threshold=0.9, state_scoring=False):
    # -- instead of going into the expansion (which may take a long time), just find direct substitutes for 
    #	objects (typically for task tree retrieval's inputs and add them to the kitchen)

    # -- list of objects and their similarity values w.r.t. other objects:
    global FOON_objectLabels

    # -- objective is to populate a list of objects that are similar to this object:
    similar_objects = []

    this_obj = O.getObjectLabel()
    
    for other_obj in FOON_objectLabels:

        if this_obj == other_obj:
            # -- be sure to avoid using the same label again:
            continue

        # -- all similarity values are pre-computed and are found in the object_similarity_index dict:
        similarity_value = float(_computeSimilarity(this_obj, other_obj, method=method))
        
        if similarity_value >= threshold:
            # -- assign the similar object's name and ID to this newly created object:
            new_object = FOON.Object(objectID=FOON_objectLabels[other_obj], objectLabel=other_obj)

            # -- copy over the attributes of the object in question (i.e., O) over to the similar objects:
            for S in O.getStatesList():
                new_object.addNewState( list(S) )

            if state_scoring:
                # -- the idea is to use word embedding models to determine if a substitute object 
                # 	has some association to the states we are about to assign to it:

                # -- we will want an average similarity score that exceeds the required threshold:
                avg_state_similarity, count = 0.0, 0

                # -- for the word vector, we need to replace whitespace with underscores:
                object_label = str(other_obj).replace(' ', '_')

                for S in new_object.getStatesList():
                    state_label = S[1].split(' ')
                    if len(state_label) < 2:
                        # -- usually single-worded state labels will be better suited for measurement
                        #	and we will avoid states like 'ingredients inside' or 'in bowl'
                        value = float(_computeSimilarity(object_label, state_label[0], method=method))
                        avg_state_similarity += value

                        # -- increment counter for measurable states:
                        count += 1
                    #endif
                #endfor

                # -- if number of measurable states is 0 or average is 0, then do not add this object:
                if count == 0 or avg_state_similarity == 0:
                    continue

                # -- if the average score is below the threshold, then do not add this object:
                avg_state_similarity = avg_state_similarity / count * 1.0
                if avg_state_similarity < threshold:
                    continue
            #endif

            similar_objects.append(new_object)
        #endif
    #endfor

    return similar_objects
#enddef


def _prepareExpansion():
    # NOTE: this function is used to gather details about the expansion method:
    print('\n -- [FOON-gen] : Please provide the following details that are needed for the expansion process:')

    global expansion_model, expansion_threshold

    if expansion_model is None:
        # -- we can either use WordNet or Concept-Net to measure similarity values (note, however, that Wordnet is MUCH faster)
        response = input("\n\ta) Perform expansion using:\n\t\t1) WordNet,\n\t\t2) Concept-Net,\n\t\t3) spacy?\t[1/2/3] (default: 3 - spacy) > ")
        expansion_model = "spacy"
        if response == "1":
            expansion_model = "WordNet"
        elif response == "2":
            expansion_model = "Concept-Net"
    else:
        print("\n\ta) Expansion method indicated as '" + expansion_model + "'!")

    if expansion_threshold is None:
        # -- NLTK's word distance metrics return a value that reflects similarity depending on the function used;
        #	we use the Wu-Palmer metric, which will return a value from 0 to 1.0, where 1.0 means that two words are synonymous	
        expansion_threshold = 0.9
        try:
            response = input("\n\tb) Provide a threshold value for object similarity (between 0.0 and 1.0 -- default: 0.9) > ")
            expansion_threshold = float(response)
        except ValueError:
            pass
    else:
        print("\n\tb) Threshold of " + str(expansion_threshold) + " has already been given!")

    # -- instead of attempting to expand a FOON based on all possible objects found in the object index of FOON,
    #	we can instead permit a customized subset of objects for expansion.
    custom_object_list = None
    use_custom_list = input("\n\tc) Use all objects for semantic similarity file? [Y/N] (default: Y) > ")

    if use_custom_list.lower() == 'n':
        custom_object_list = []

        # -- NOTE: you will need to create a new file that has subset of object labels for comparison:
        _file = open(input("  -- Please type in PATH and NAME to custom object index: > "), 'r')
        for L in _file.readlines():
            if L.startswith("//"):
                continue
            
            _parts = L.split("\t"); _object = _parts[1]
            if len(L.split("\t")) == 2:
                custom_object_list.append([_object, 1])
            else:
                custom_object_list.append([_object, _parts[2]])
            #endif
        #endfor
        print('  -- Added a total of ' + str(len(custom_object_list)) + ' items for expansion!')
    #endif

    # -- idea: use Concept-Net to decide on states being similar to one another (still needs testing):
    use_state_suggestion = input('\n\td) Perform state association checking (to see if objects match assigned states)? (default: N) [Y/N] > ')
    state_suggestion = True if use_state_suggestion.lower() == "y" else False

    print()

    return expansion_model, expansion_threshold, custom_object_list, state_suggestion
#enddef


def _expandNetwork_nontext():	
    expansion_model, given_threshold, custom_object_list, flag_state_check = _prepareExpansion()

    # NOTE: first, we start off with the base set of nodes and functional units from level 3:
    global FOON_nodes, FOON_functionalUnits, FOON_objectLabels, FOON_objectsToUnits

    expanded_FOON, expanded_nodes = [], []

    # -- copy over existing objects:
    for node in FOON_nodes[2]:
        expanded_nodes.append(node)

    for FU in FOON_functionalUnits[2]:
        expanded_FOON.append(FU)

    print('\n -- [FOON-EXP] : Beginning expansion...')

    # NOTE: for expansion, we use the highest level of FOON (level 3), since it will be the most "complete" version:
    # -- this is why we use "FOON_nodes[2]".
    for N in tqdm.tqdm(FOON_nodes[2], desc='Performing expansion...'):

        if not isinstance(N, FOON.Object):
            # -- remember that nodes list contains both objects and motions together, so skip over motion nodes:
            continue

        if custom_object_list and N.getObjectLabel() not in custom_object_list:
            # -- if there is a pre-defined list of objects to consider for expansion and an
            #	object is not on the list, skip it.
            continue

        # -- we look for objects that already exist in FOON to create new objects that are deemed "similar".
        expanded_objects = _findObjectSubstitute(N, method=expansion_model,threshold=given_threshold, state_scoring=flag_state_check)

        for obj in expanded_objects:
            # -- recall that each expanded object will be the same as N, except by the name and ID.		

            # -- we then make sure that this object does not exist in FOON (specifically, the list of nodes) already:
            index = -1
            for M in expanded_nodes:
                if not isinstance(M, FOON.Object):
                    continue
                
                # -- check if copied object already exists in the list of nodes:
                if obj.equals_functions[2](M):
                    index = expanded_nodes.index(M)
                    break
                #endif
            #endfor

            # -- if we did not find the object in the list, then we can proceed to adding the object to FOON's nodes:
            if index == -1:
                index = len(expanded_nodes)	
                expanded_nodes.append(obj)

                # NOTE: verbose stuff...
                if verbose:
                    print("added:")
                    expanded_nodes[index].print_functions[2]()
                    print('to replace:')
                    N.print_functions[2]()
                    print('-----------')
                #endif
            #endif

            # -- now that we have made sure the node is there, we then get the appropriate mapping to the copied object as object X:
            copiedObject = expanded_nodes[index]

            # NEXT, we look at all instances of functional units present in FOON, which we will then be using to copy objects over.
            # -- we will look for instances of object Y and then replace with instances of object X.
            for FU in FOON_objectsToUnits[2][N]:

                newFU = FOON.FunctionalUnit()	# -- blank functional unit object to keep track of copy
                changed = 0				# -- this variable will tell us if there were any changes made to the functional unit!

                # -- we begin by looking at the reference unit's OUTPUT objects...
                for M in FU.getOutputNodes():

                    # NOTE: There are certain cases we need to consider:

                    # 1) We found the EXACT instance of Y that we want to replace with the copied object of type X. 	
                    if N.equals_lvl3(M):
                        # -- no need to check or adjust the object; we just directly add the newly copied object to the functional unit:
                        newFU.addObjectNode(copiedObject, is_input=False, is_active_motion=FU.getOutputDescriptor(FU.getOutputList().index(M)))
                        changed += 1
                    
                    # 2) We find an object instance of Y but in a different state than what we are looking for in X.
                    # 	However, in this case, we are still changing this object from Y to X.
                    elif N.getObjectType() == M.getObjectType() or N.getObjectLabel() == M.getObjectLabel():
                        # -- get the right ID, states and label for the new object X and assign it to the adjusted object:
                        adjustedObject = FOON.Object(objectID=copiedObject.getObjectType(), objectLabel=copiedObject.getObjectLabel())
                        adjustedObject.setStatesList( list(M.getStatesList()) )

                        # -- add the object as we normally would to the functional unit:
                        newFU.addObjectNode(adjustedObject, is_input=False, is_active_motion=FU.getOutputDescriptor(FU.getOutputList().index(M)))								
                        changed += 1

                    # 3) We found an object that is not of type Y but that may or may not refer to Y such that we need to adjust it to refer to X.
                    # -- e.g. : when dealing with containers that hold ingredient Y, it should now hold ingredient X:
                    else:
                        # -- keep note of the original (remember, non-Y) object's type and label:
                        adjustedObject = FOON.Object(objectID=M.getObjectType(), objectLabel=M.getObjectLabel())

                        # -- set the states of the object to the exact states seen for the original object:
                        adjustedObject.setStatesList( list(M.getStatesList()) )

                        # -- found_ref :- flag to determine if we found the substituted object name in the ingredients list:
                        found_ref = False

                        # 3a) Check the ingredients that are contained in an object for any references to the original object:
                        adjusted_ingredients = M.getIngredients()
                        if N.getObjectLabel() in adjusted_ingredients:
                            adjusted_ingredients[adjusted_ingredients.index(N.getObjectLabel())] = copiedObject.getObjectLabel()
                            found_ref = True
    
                        if found_ref:
                            # -- set the new object's ingredients to the adjusted list:
                            adjustedObject.setIngredients(adjusted_ingredients)

                        # 3b) Maybe the object does not CONTAIN Y, but it may have some relationship to Y, which is reflected by related object value:
                        for x in range(len(adjustedObject.getStatesList())):
                            if N.getObjectLabel() == adjustedObject.getRelatedObject(x):
                                # -- set the related object X to where Y used to be:
                                adjustedObject.setRelatedObject(x, relatedObj=copiedObject.getObjectLabel())
                                found_ref = True
                            #endif
                        #endfor

                        if found_ref:
                            # -- check to see if this object exists already in FOON:
                            index = -1
                            for J in expanded_nodes:
                                if not isinstance(J, FOON.Object):
                                    continue

                                if adjustedObject.equals_lvl3(J):
                                    index = expanded_nodes.index(J)
                                    break
                                #endif
                            #endfor

                            if index == -1:
                                index = len(expanded_nodes)	
                                expanded_nodes.append(adjustedObject)
                            #endif

                            # -- add the (potentially new) object to the functional unit as normal:
                            newFU.addObjectNode(expanded_nodes[index], is_input=False, is_active_motion=FU.getOutputDescriptor(FU.getOutputList().index(M)))		
                            changed += 1

                        else:
                            # 3) c. This object has not one reference of Y, so we just add this as normal.
                            newFU.addObjectNode(M, is_input=False, is_active_motion=FU.getOutputDescriptor(FU.getOutputList().index(M)))
                        #endif
                    #endif
                #endfor
                
                # -- next, we take a look at the reference unit's INPUT objects...
                for M in FU.getInputNodes():

                    # NOTE: There are certain cases we need to consider:

                    # 1) We found the EXACT instance of Y that we want to replace with the copied object of type X. 	
                    if N.equals_lvl3(M):
                        # -- no need to check or adjust the object; we just directly add the newly copied object to the functional unit:
                        newFU.addObjectNode(copiedObject, is_input=True, is_active_motion=FU.getInputDescriptor()[FU.getInputList().index(M)])
                        changed += 1
                    
                    # 2) We find an object instance of Y but in a different state than what we are looking for in X.
                    # 	However, in this case, we are still changing this object from Y to X.
                    elif N.getObjectType() == M.getObjectType() or N.getObjectLabel() == M.getObjectLabel():
                        # -- get the right ID, states and label for the new object X and assign it to the adjusted object:
                        adjustedObject = FOON.Object(objectID=copiedObject.getObjectType(), objectLabel=copiedObject.getObjectLabel())
                        adjustedObject.setStatesList(M.getStatesList())

                        # -- add the object as we normally would to the functional unit:
                        newFU.addObjectNode(adjustedObject, is_input=True, is_active_motion=FU.getInputDescriptor()[FU.getInputList().index(M)])								
                        changed += 1

                    # 3) We found an object that is not of type Y but that may or may not refer to Y such that we need to adjust it to refer to X.
                    # -- e.g. : when dealing with containers that hold ingredient Y, it should now hold ingredient X:
                    else:
                        
                        # -- keep note of the original (remember, non-Y) object's type and label:
                        adjustedObject = FOON.Object(objectID=M.getObjectType(), objectLabel=M.getObjectLabel())

                        # -- set the states of the object to the exact states seen for the original object:
                        adjustedObject.setStatesList(M.getStatesList())

                        found_ref = False

                        # 3a) Check the ingredients that are contained in an object for any references to the original object:
                        adjusted_ingredients = M.getIngredients()
                        if N.getObjectLabel() in adjusted_ingredients:
                            adjusted_ingredients[adjusted_ingredients.index(N.getObjectLabel())] = copiedObject.getObjectLabel()
                            found_ref = True
    
                        if found_ref:
                            # -- set the new object's ingredients to the adjusted list:
                            adjustedObject.setIngredients(adjusted_ingredients)

                        # 3b) Maybe the object does not CONTAIN Y, but it may have some relationship to Y, which is reflected by related object value:
                        for x in range(len(adjustedObject.getStatesList())):
                            if N.getObjectLabel() == adjustedObject.getRelatedObject(x):
                                # -- set the related object X to where Y used to be:
                                adjustedObject.setRelatedObject(x, relatedObj=copiedObject.getObjectLabel())
                                found_ref = True
                            #endif
                        #endfor

                        if found_ref:
                            # -- check to see if this object exists already in FOON:
                            index = -1
                            for J in expanded_nodes:
                                if not isinstance(J, FOON.Object):
                                    continue

                                if adjustedObject.equals_lvl3(J):
                                    index = expanded_nodes.index(J)
                                    break
                                #endif
                            #endfor

                            if index == -1:
                                index = len(expanded_nodes)	
                                expanded_nodes.append(adjustedObject)
                            #endif

                            # -- add the (potentially new) object to the functional unit as normal:
                            newFU.addObjectNode(expanded_nodes[index], is_input=True, is_active_motion=FU.getInputDescriptor(FU.getInputList().index(M)))										
                            changed += 1

                        else:
                            # 3) c. This object has not one reference of Y, so we just add this as normal.
                            newFU.addObjectNode(M, is_input=True, is_active_motion=FU.getInputDescriptor(FU.getInputList().index(M)))
                        #endif

                    #endif
                #endfor

                # -- next, we need to create a new motion node of the exact same type and add it to this functional unit;
                #	however, this will only be added if the functional unit has been changed or not.
                tempMotion = FOON.Motion(motionID=FU.getMotion().getMotionType(), motionLabel=FU.getMotion().getMotionLabel())
                newFU.setTimes(FU.getStartTime(), FU.getEndTime())
                newFU.setSuccessRate(FU.getSuccessRate())
                newFU.setIndication(FU.getIndication())
                newFU.setMotion(tempMotion)

                # FINALLY, we have completed copying the functional unit.
                # -- what we do now is add it to the list of candidate units that we want to add to FOON-EXP:
                if changed > 0:
                    # -- add the motion node for the new functional unit we created via expansion:
                    expanded_nodes.append(tempMotion)

                    # -- add the expanded functional unit if it does not exist:
                    already_exists = False
                    for _unit in expanded_FOON:
                        if _unit.equals_functions[2](newFU):
                            already_exists = True
                            break
    
                    if not already_exists:
                        expanded_FOON.append(newFU)

                    if verbose:
                        print('Original:')
                        FU.printFunctionalUnit_lvl3()
                        print('Expanded:')
                        newFU.printFunctionalUnit_lvl3()
                        input()
                    #endif
                #endif
            #endfor
        #endfor
    #endfor

    print(' -- [FOON-EXP] : Total number of expanded functional units: ' + str(len(expanded_FOON)))

    # -- now we will write the functional units to a new file:
    expanded_file = "expanded_FOON-thr=" + str(given_threshold) + "-method=" + str(expansion_model) + "-NT.txt"
    _file = open(expanded_file, 'w')

    global file_name

    _file.write('# Original File:\t' + file_name)
    _file.write('# Date created:\t' + str(datetime.today().strftime('%d.%m.%Y')) + '\n')
    _file.write('# Expansion Method:\t' + str(expansion_model) + '\n')
    _file.write('# Similarity Threshold:\t' + str(given_threshold) + '\n')
    _file.write('//\n')

    for FU in tqdm.tqdm(list(expanded_FOON)):
        _file.write(FU.getFunctionalUnitText())

    print(' -- [FOON-gen] : Expanded universal FOON written to ' + (expanded_file) + "' (using threshold=" + str(given_threshold) + ")!")
    _file.close()

    # TODO: test this updated function...

    global is_expansion_done; is_expansion_done = True

    return expanded_file
#enddef


def _expandNetwork_text():
    expansion_method, given_threshold, custom_object_list, flag_state_check = _prepareExpansion()

    # NOTE: first, we start off with the base set of nodes and functional units from level 3:
    global FOON_nodes, FOON_functionalUnits, FOON_objectLabels, FOON_objectsToUnits

    # NOTE: We use a set structure to preserve uniqueness among strings of functional units:
    new_units = set()

    similarity_index = {}

    for FU in FOON_functionalUnits[2]:
        # -- this way, we note what we already have in our present, regular universal FOON:
        new_units.add(FU.getFunctionalUnitText())

    for X in tqdm.tqdm(FOON_objectLabels, desc='Performing expansion...'):

        if custom_object_list and X not in custom_object_list:
            # -- if there is a pre-defined list of objects to consider for expansion and an
            #	object is not on the list, skip it.
            continue

        for Y in FOON_objectLabels:
            # -- we are looking for different object pairs and finding those that share significant similarity

            if X == Y: continue

            # -- use memoization if possible, else just look up similarity value:
            similarity_value = 0
            if (Y in similarity_index and X in similarity_index[Y]) or (X in similarity_index and Y in similarity_index[X]):
                similarity_value = 1.0
            else:
                similarity_value = float(_computeSimilarity(X, Y, method=expansion_method))
            #endif

            if similarity_value >= given_threshold:

                # -- to add some relations for quick lookups:
                if X not in similarity_index:
                    similarity_index[X] = set()

                if Y not in similarity_index:
                    similarity_index[Y] = set()

                similarity_index[X].add(Y)
                similarity_index[Y].add(X)

                for N in FOON_nodes[2]:
        
                    if not isinstance(N, FOON.Object):
                        # -- remember that nodes list contains both objects and motions together, so skip over motion nodes:
                        continue

                    for FU in FOON_objectsToUnits[2][N]:
                        # -- we go through all functional units associated with a given object N:

                        # NOTE: this is how this section will work:
                        #	1. Iterate through every input object's text and make changes (while possibly noting relativity of states to objects)
                        #	2. Interage through every output object's text with same criteria
                        #	3. Append text for inputs, outputs, and motion to one single string called 'copied_unit'.
                        #	4. Append single string from previous step to a set of strings referring to expanded units.
                        copied_unit, skip, found = str(), False, False

                        for x in range(FU.getNumberOfInputs()):
                            # -- first, we start with INPUT nodes:
                            object_text = str(FU.getInputNodeText(x))

                            if Y in object_text: # NOTE: checking if substring exists in string
                                # -- this means we found something similar to X that we will be substituting via text:
                                items = object_text.split('\n') 

                                # NOTE: the following variables will ONLY be used to compute "associativity" of states to the new object:
                                flag_substitution = False # -- determines if a substitution has been made to this object
                                found = True
                                avg_state_similarity, count = 0.0, 0 # -- keep track of cumulative similarity and number of compared states

                                for y in range(len(items)):
                                    line = items[y]

                                    # NOTE: there are two main parts to check when substituting objects:
                                    #	1. Check the object label and ID
                                    #	2. Check the ingredients for each object
                                    if line.startswith("O"):
                                        # -- parsing through the object labels:
                                        objectParts = line.split("O")
                                        objectParts = objectParts[1].split("\t")

                                        if objectParts[1] == Y:
                                            # -- if we found instance of Y, we substitute with X:
                                            objectParts[0] = "O" + str(FOON_objectLabels[X]); objectParts[1] = X
                                            flag_substitution = True
                                        else:
                                            objectParts[0] = "O" + str(objectParts[0])
                                        #endif

                                        # -- combining new line together:
                                        items[y] = '\t'.join(objectParts)

                                    elif line.startswith("S"):
                                        # -- parsing through the state labels, specifically for INGREDIENTS:
                                        stateParts = line.split("\t"); stateParts = list(filter(None, stateParts))

                                        if flag_substitution and flag_state_check:
                                            # -- this means that we have swapped an object for another, so we should not care about ingredients:
                                            state_label = str(stateParts[1]).split(' ')

                                            # -- usually single-worded state labels will be better suited for measurement
                                            #	and we will avoid states like 'ingredients inside' or 'in bowl'
                                            if len(state_label) < 2:
                    
                                                # -- for the word vector, we need to replace whitespace with underscores:
                                                object_label = str(X).replace(' ', '_')
                                                
                                                value = float(_computeSimilarity(object_label, state_label[0], method=expansion_method))
                                                avg_state_similarity += value

                                                # -- increment counter for measurable states:
                                                count += 1
                                            #endif
                                        else:
                                            if len(stateParts) > 2:
                                                revised = None
                                                # -- we can either have ingredients (enclosed in {...}) or a relative object (enclosed in [...]):
                                                if '[' in stateParts[2] or ']' in stateParts[2]:
                                                    # -- relative object:
                                                    ingredients = [ stateParts[2] ]
                                                    ingredients = ingredients[0].split("[")
                                                    ingredients = ingredients[1].split("]")
                                                    revised = '[' + (X if ingredients[0] == Y else ingredients[0]) + ']' 
                                                else:
                                                    # -- ingredient object:
                                                    revised = '{'
                                                    ingredients = [ stateParts[2] ]
                                                    ingredients = ingredients[0].split("{")
                                                    ingredients = ingredients[1].split("}")

                                                    # -- we then need to make sure that there are ingredients to be read:
                                                    if len(ingredients) > 0:
                                                        ingredients = ingredients[0].split(",")
                                                        for i in range(len(ingredients)):
                                                            if ingredients[i] == Y:
                                                                ingredients[i] = X
                                                            revised += ingredients[i]
                                                            if i < (len(ingredients) - 1):
                                                                revised += ','
                                                    revised += '}'
                                                #endif
                                                stateParts[2] = revised
                                            #endif
                                        #endif

                                        items[y] = '\t'.join(stateParts)
                                    #endif
                                #endfor

                                if flag_state_check:
                                    if count == 0:
                                        copied_unit += '\n'.join(items)
                                    else:
                                        avg_state_similarity = avg_state_similarity / count * 1.0
                                        if avg_state_similarity >= 0.3:
                                            # -- this means that the states are somewhat related to the new object:
                                            copied_unit += '\n'.join(items)
                                        else:
                                            # -- if it is below threshold, then we cannot safely substitute the object, so we should skip adding this functional unit:
                                            skip = True
                                        #endif
                                    #endif
                                else:
                                    copied_unit += '\n'.join(items)
                                #endif
                            else:
                                # -- this means the object has no trace of the substituted object:
                                copied_unit += object_text	
                            #endif	
                        #endfor

                        if skip or copied_unit == '':
                            continue

                        copied_unit += FU.getMotionForFile()

                        for x in range(FU.getNumberOfOutputs()):
                            # -- next, we look at OUPUT nodes:
                            object_text = str(FU.getOutputNodeText(x))

                            if Y in object_text: # NOTE: checking if substring exists in string
                                # -- this means we found something similar to X that we will be substituting via text:
                                items = object_text.split('\n') 

                                # NOTE: the following variables will ONLY be used to compute "associativity" of states to the new object:
                                flag_substitution = False # -- determines if a substitution has been made to this object
                                found = True
                                avg_state_similarity, count = 0.0, 0 # -- keep track of cumulative similarity and number of compared states

                                for y in range(len(items)):
                                    line = items[y]

                                    # NOTE: there are two main parts to check when substituting objects:
                                    #	1. Check the object label and ID
                                    #	2. Check the ingredients for each object
                                    if line.startswith("O"):
                                        # -- parsing through the object labels:
                                        objectParts = line.split("O"); objectParts = objectParts[1].split("\t")

                                        if objectParts[1] == Y:
                                            # -- if we found instance of Y, we substitute with X:
                                            objectParts[0] = "O" + str(FOON_objectLabels[X]); objectParts[1] = X
                                            flag_substitution = True
                                        else:
                                            objectParts[0] = "O" + str(objectParts[0])
                                        #endif

                                        # -- combining new line together:
                                        items[y] = '\t'.join(objectParts)

                                    elif line.startswith("S"):
                                        # -- parsing through the state labels, specifically for INGREDIENTS:
                                        stateParts = line.split("\t"); stateParts = list(filter(None, stateParts))

                                        if flag_substitution and flag_state_check:
                                            # -- this means that we have swapped an object for another, so we should not care about ingredients:
                                            state_label = str(stateParts[1]).split(' ')

                                            # -- usually single-worded state labels will be better suited for measurement
                                            #	and we will avoid states like 'ingredients inside' or 'in bowl'
                                            if len(state_label) < 2:
                    
                                                # -- for the word vector, we need to replace whitespace with underscores:
                                                object_label = str(X).replace(' ', '_')
                                                
                                                value = float(_computeSimilarity(object_label, state_label[0], method=expansion_method))
                                                avg_state_similarity += value

                                                # -- increment counter for measurable states:
                                                count += 1
                                            #endif
                                        else:
                                            if len(stateParts) > 2:
                                                revised = None
                                                # -- we can either have ingredients (enclosed in {...}) or a relative object (enclosed in [...]):
                                                if '[' in stateParts[2] or ']' in stateParts[2]:
                                                    # -- relative object:
                                                    ingredients = [ stateParts[2] ]
                                                    ingredients = ingredients[0].split("[")
                                                    ingredients = ingredients[1].split("]")
                                                    revised = '[' + (X if ingredients[0] == Y else ingredients[0]) + ']' 
                                                else:
                                                    # -- ingredient object:
                                                    revised = '{'
                                                    ingredients = [ stateParts[2] ]
                                                    ingredients = ingredients[0].split("{")
                                                    ingredients = ingredients[1].split("}")

                                                    # -- we then need to make sure that there are ingredients to be read:
                                                    if len(ingredients) > 0:
                                                        ingredients = ingredients[0].split(",")
                                                        for i in range(len(ingredients)):
                                                            if ingredients[i] == Y:
                                                                ingredients[i] = X
                                                            revised += ingredients[i]
                                                            if i < (len(ingredients) - 1):
                                                                revised += ','
                                                    revised += '}'
                                                #endif
                                                stateParts[2] = revised
                                            #endif
                                        #endif

                                        items[y] = '\t'.join(stateParts)
                                    #endif
                                #endfor

                                if flag_state_check:
                                    if count == 0:
                                        copied_unit += '\n'.join(items)
                                    else:
                                        avg_state_similarity = avg_state_similarity / count * 1.0
                                        if avg_state_similarity >= 0.3:
                                            # -- this means that the states are somewhat related to the new object:
                                            copied_unit += '\n'.join(items)
                                        else:
                                            # -- if it is below threshold, then we cannot safely substitute the object, so we should skip adding this functional unit:
                                            skip = True
                                        #endif
                                    #endif
                                else:
                                    copied_unit += '\n'.join(items)
                                #endif
                            else:
                                # -- this means the object has no trace of the substituted object:
                                copied_unit += object_text	
                            #endif	
                        #endfor

                        if skip or copied_unit.rstrip() == "":
                            continue

                        if found and verbose:
                            print(FU.getFunctionalUnitText())
                            print(Y + ' --> ' + X)
                            print(copied_unit)
                        
                        copied_unit += '//\n'

                        new_units.add(copied_unit)
                    #endfor
                #endif
            #endfor	
        #endfor
    #endfor

    # -- having expanded everything as text, we can then proceed to writing all units to a new file:
    expanded_file = "expanded_FOON-thr=" + str(given_threshold) + "-method=" + str(expansion_method) + ".txt"
 
    _file = open(expanded_file, 'w')

    global file_name

    _file.write('# Original File:\t' + file_name)
    _file.write('# Date created:\t' + str(datetime.today().strftime('%d.%m.%Y')) + '\n')
    _file.write('# Expansion Method:\t' + str(expansion_method) + '\n')
    _file.write('# Similarity Threshold:\t' + str(given_threshold) + '\n')
    _file.write('//\n')

    for FU in tqdm.tqdm(new_units):
        _file.write(FU)

    _file.close()

    print("\n -- [FOON-gen] : Expanded universal FOON written to '" + (expanded_file) + "' (using threshold=" + str(given_threshold) + ")!")

    global is_expansion_done; is_expansion_done = True

    return expanded_file
#enddef


def _populateCategoryList():
    import json

    global contents, FOON_objectClusters, FOON_objectCluster_index

    print("\n -- [FOON-gen] : Loading predefined object categories index..")

    # -- two-staged check for the categories file (this is built by the 'FOON_parser' script):
    try:
        contents = json.load( open('FOON_categories.json', 'r') )
        FOON_objectClusters = contents['object_categories']
    except FileNotFoundError:
        print(" -- WARNING: File 'FOON_categories.json' not found in current directory!")
        path_to_categories_file = input("\t-- Please provide the path to the 'FOON_categories.json' file: > ")

        try:
            contents = json.load( open(path_to_categories_file, 'r') )
            FOON_objectClusters = contents['object_categories']
        except FileNotFoundError:
            print("\t-- Please run the 'FOON_parser.py' script and make sure to have the 'FOON_categories.txt' file ready.")
            return -1
    #endtry

    # -- if we successfully loaded the object categories/clusters, then we will assign index values to them:
    count = 0
    for key in FOON_objectClusters:
        # -- index values for cluster labels will be negative:
        count -= 1
        FOON_objectCluster_index[key] = count

    return 1
#enddef


def _compressNetwork():
    global file_name, verbose, FOON_functionalUnits

    global FOON_functionalUnits_compressed, FOON_nodes_compressed
    FOON_nodes_compressed, FOON_functionalUnits_compressed = [], []

    global FOON_objectClusters,FOON_objectCluster_index
    if not FOON_objectClusters:
        result = _populateCategoryList()
        if result != 1:
            return None

    print("\n -- [FOON-gen] : Creating compressed (abstracted) FOON...")

    # -- for a generalized FOON (containing object categories in lieu of object types), we use a lvl. 3 FOON:
    for FU in tqdm.tqdm(FOON_functionalUnits[2], desc='Performing compression (iterating through all functional units)...'):
 
        tempFU = FOON.FunctionalUnit()

        uncategorized_nodes = []
        obj_to_category = {}

        # -- go through all input/output object nodes and make them generalized:
        for T in FU.getInputList():

            loc = FU.getInputList().index(T)
            obj_in_category = False
            tempObject = None

            # NOTE: key :- cluster or category name; obj :- name of object under cluster key
            for key in FOON_objectClusters:
                for obj in FOON_objectClusters[key]:

                    # -- we will check if some object T exists in an object category/cluster:
                    if obj == T.getObjectLabel():

                        # -- we will keep track of the original object label and what we compressed it to:
                        obj_to_category[obj] = key

                        # -- get the object and create new Category object based on it:
                        tempObject = FOON.Object(objectID=FOON_objectCluster_index[key], objectLabel=key)

                        for S in T.getStatesList():
                            state_copy = list(S)
                            # -- make replacement of an object's label by its category name:
                            if obj in state_copy:
                                state_copy[state_copy.index(obj)] = key
                            tempObject.addNewState(state_copy)

                        obj_exists_in_FOON = False
                        
                        for U in tempFU.getInputList():
                            if U.equals_functions[1](tempObject):
                                obj_exists_in_FOON = True
                                break
                        
                        if obj_exists_in_FOON is False:
                            index = -1
                            for N in FOON_nodes_compressed:
                                if isinstance(N, FOON.Object):
                                    if N.equals_functions[1](tempObject):
                                        index = FOON_nodes_compressed.index(N)
                                        break

                            if index == -1:
                                tempFU.addObjectNode(tempObject, is_input=True, is_active_motion=FU.getInputDescriptor(loc))
                                FOON_nodes_compressed.append(tempObject)
                            else:
                                tempFU.addObjectNode(FOON_nodes_compressed[index], is_input=True, is_active_motion=FU.getInputDescriptor(loc))

                    #endif
                #endfor
            #endfor					

            if tempObject is None:
                # -- this means that the object is not in any category; 
                #       therefore, we need to revise this after we have identified all objects to compress:
                uncategorized_nodes.append(T)

        for T in uncategorized_nodes:
            # -- we will add an object that does not belong to any category or cluster:

            # -- however, we must first see if there are any labels (mainly the related object)
            #       that needs to be compressed as a category / cluster name:
            tempObject = FOON.Object(objectID=T.getID(), objectLabel=T.getLabel())
            tempObject.setStatesList(T.getStatesList())
            
            for x in range(tempObject.getNumberOfStates()):
                related_obj = tempObject.getRelatedObject(x)

                if related_obj is None:
                    continue

                if related_obj in obj_to_category:
                    # -- here, we replace the relative object's name with the category label:
                    tempObject.setRelatedObject(x, relatedObj=obj_to_category[related_obj])

            # -- now that we have compressed this object (or not), we then check to see if it
            #       already exists in the compressed FOON's node list before adding to the unit:
            index = -1
            for N in FOON_nodes_compressed:
                if isinstance(N, FOON.Object):
                    if N.equals_functions[1](tempObject):
                        index = FOON_nodes_compressed.index(N)
                        break

            if index == -1:
                # -- if there is no reference to this node in the compressed FOON's node list, then we add it:
                index = len(FOON_nodes_compressed)
                FOON_nodes_compressed.append(tempObject)

            tempFU.addObjectNode(FOON_nodes_compressed[index], is_input=True, is_active_motion=FU.getInputDescriptor(FU.getInputList().index(T)))

        #endfor	

        # -- motions are simply copied over:
        tempFU.setMotion(FU.getMotion())
        tempFU.setTimes(FU.getStartTime(), FU.getEndTime())

        uncategorized_nodes = []
        obj_to_category = {}

        for T in FU.getOutputList():

            loc = FU.getOutputList().index(T)
            obj_in_category = False
            tempObject = None

            # NOTE: key :- cluster or category name; S :- name of object under cluster key
            for key in FOON_objectClusters:
                for obj in FOON_objectClusters[key]:

                    # -- we will check if some object T exists in an object category/cluster:
                    if obj == T.getObjectLabel():

                        # -- we will keep track of the original object label and what we compressed it to:
                        obj_to_category[obj] = key

                        # -- get the object and create new Category object based on it:
                        tempObject = FOON.Object(objectID=FOON_objectCluster_index[key], objectLabel=key)

                        for S in T.getStatesList():
                            state_copy = list(S)
                            # -- make replacement of an object's label by its category name:
                            if obj in state_copy:
                                state_copy[state_copy.index(obj)] = key
                            tempObject.addNewState(state_copy)
                        
                        obj_in_category = True
                        obj_exists_in_FOON = False
                        
                        for U in tempFU.getOutputList():
                            if U.equals_functions[1](tempObject):
                                obj_exists_in_FOON = True
                                break

                        if obj_exists_in_FOON is False:
                            index = -1
                            for N in FOON_nodes_compressed:
                                if isinstance(N, FOON.Object):
                                    if N.equals_functions[1](tempObject):
                                        index = FOON_nodes_compressed.index(N)
                                        break

                            if index == -1:
                                tempFU.addObjectNode(tempObject, is_input=False, is_active_motion=FU.getOutputDescriptor(loc))
                                FOON_nodes_compressed.append(tempObject)
                            else:
                                tempFU.addObjectNode(FOON_nodes_compressed[index], is_input=False, is_active_motion=FU.getOutputDescriptor(loc))

                    #endif 	
                #endfor
            #endfor					

            if obj_in_category is False:
                # -- this means that the object is not in any category; 
                #       therefore, we need to revise this after we have identified all objects to compress:
                uncategorized_nodes.append(T)

        for T in uncategorized_nodes:
            # -- we will add an object that does not belong to any category or cluster:

            # -- however, we must first see if there are any labels (mainly the related object)
            #       that needs to be compressed as a category / cluster name:
            tempObject = FOON.Object(objectID=T.getID(), objectLabel=T.getLabel())
            tempObject.setStatesList(T.getStatesList())
            
            for x in range(tempObject.getNumberOfStates()):
                related_obj = tempObject.getRelatedObject(x)

                if related_obj is None:
                    continue

                if related_obj in obj_to_category:
                    # -- here, we replace the relative object's name with the category label:
                    tempObject.setRelatedObject(x, relatedObj=obj_to_category[related_obj])

            # -- now that we have compressed this object (or not), we then check to see if it
            #       already exists in the compressed FOON's node list before adding to the unit:
            index = -1
            for N in FOON_nodes_compressed:
                if isinstance(N, FOON.Object):
                    if N.equals_functions[1](tempObject):
                        index = FOON_nodes_compressed.index(N)
                        break

            if index == -1:
                # -- if there is no reference to this node in the compressed FOON's node list, then we add it:
                index = len(FOON_nodes_compressed)
                FOON_nodes_compressed.append(tempObject)

            tempFU.addObjectNode(FOON_nodes_compressed[index], is_input=False, is_active_motion=FU.getOutputDescriptor(FU.getOutputList().index(T)))

        #endfor	
        
        if verbose:
            tempFU.printFunctionalUnit_lvl3()
            input("testing...")
    
        # -- now that we have created generalized object nodes in a new functional unit,
        #		we check to see if we have the generalized unit already in FOON-GEN:
        FU_exists_in_FOON = False

        for U in FOON_functionalUnits_compressed:
            if U.equals_lvl3(tempFU):
                FU_exists_in_FOON = True 
                break

        if FU_exists_in_FOON is False:
            # -- if the functional unit does not exist in FOON-GEN, then just add it:
            FOON_functionalUnits_compressed.append(tempFU)

    #endfor	

    global file_name

    # -- after creating FOON-GEN, we will straight-away output everything to a file:
    compressed_file = "compressed_FOON-original=" + os.path.splitext(file_name)[0] + ".txt"

    _file = open(compressed_file, 'w')

    _file.write('# Original File:\t' + file_name + '\n')
    _file.write('# Date created:\t' + str(datetime.today().strftime('%d.%m.%Y')) + '\n')
    _file.write('//\n')

    for FU in tqdm.tqdm(FOON_functionalUnits_compressed, desc='Writing compressed functional units to file...'):
        _file.write(FU.getFunctionalUnitText())

    _file.close()		

    global is_compression_done; is_compression_done = True

    print('\n -- [FOON-gen] : Compressed FOON created with the following details:')
    print("  -- Number of functional units in FOON-GEN: " + str(len(FOON_functionalUnits_compressed)))
    print("  -- Number of nodes in FOON-GEN: " + str(len(FOON_nodes_compressed)))

    _buildOutputsToUnitMap_compressed()

    print('\n -- [FOON-gen] : Compressed universal FOON written to ' + (compressed_file) + "!")

    return compressed_file
#enddef


def _buildOutputsToUnitMap_compressed():
    global FOON_functionalUnits_compressed, FOON_nodes_compressed, FOON_outputsToUnits_compressed

    for _input in FOON_nodes_compressed:
        if isinstance(_input, FOON.Object):
            procedures = []
            for _U in FOON_functionalUnits_compressed:
                for _output in _U.getOutputList():
                    if _input.equals_functions[2](_output):
                        procedures.append(_U); break
                    #endif	
                #endfor
            #endfor
            FOON_outputsToUnits_compressed[_input] = procedures
#enddef


def _abstractObjects(obj_list):
    if not obj_list:
        return None

    global FOON_objectClusters, FOON_objectCluster_index
    if not FOON_objectClusters:
        result = _populateCategoryList()
        if result != 1:
            return None

    abstracted_objects = []
    for obj in obj_list:
        tempObject = None

        for cat in FOON_objectClusters:
            if obj.getObjectLabel() in FOON_objectClusters[cat]:
                tempObject = FOON.Object(objectID=FOON_objectCluster_index[cat], objectLabel=cat)
                tempObject.setStatesList(obj.getStatesList())

        if tempObject is None:
            tempObject = FOON.Object(objectID=obj.getObjectType(), objectLabel=obj.getObjectLabel())
            tempObject.setStatesList(obj.getStatesList())

        for x in range(tempObject.getNumberOfStates()):
            related_obj = tempObject.getRelatedObject(x)

            if related_obj is None:
                continue

            for key in FOON_objectClusters:

                if related_obj in FOON_objectClusters[key]:
                    # -- here, we replace the relative object's name with the category label:
                    tempObject.setRelatedObject(x, relatedObj=key)

        abstracted_objects.append(tempObject)
    
    return abstracted_objects
#enddef


def _taskTreeRetrieval_compressed(goalType, goalState, environment=None):
    # NOTE: task tree retrieval for FOON-GEN.

    try:
        import FOON_retrieval as frt
    except ImportError:
        print(" -- ERROR: Missing FRT (FOON_retrieval.py) file!")
        print("\t-- Download here: https://github.com/davidpaulius/foon_api/src/master/")
        return

    global FOON_outputsToUnits_compressed

    hierarchy_level = 3; searchMap = FOON_outputsToUnits_compressed

    # -- sometimes we may define a specific kitchen; other times, we just stick to default:
    if not environment:
        file = input('  -- Please provide the name of the file with KITCHEN ITEMS (press ENTER ONLY to use default): > ')
        if file == '':
            environment = frt._loadKitchenList() # -- use default 'FOON-input_only_nodes.txt'
        else:
            environment = frt._loadKitchenList(file) # -- use a different text file with kitchen items
        #endif
    #endif

    goalNode = FOON.Object(objectID=int(goalType), objectLabel=None)
    for x in goalState:
        goalNode.addNewState([int(x), None, []])
    #endif

    # -- we will identify different target goal nodes that have the same object/state combination:
    goals = []

    possible_goals = _abstractObjects([goalNode])

    # -- FIRST, we need to identify possible GENERALIZED goal nodes:
    index = -1
    for N in FOON_nodes_compressed:
        if isinstance(N, FOON.Object):

            for G in possible_goals:
                if N.equals_lvl1(G) and N.isSameStates_ID_only(G):
                    index = FOON_nodes_compressed.index(N)
                    goals.append(FOON_nodes_compressed[index])

        #endif
    #endfor

    if not goals or index == -1:
        print("Goal " + goalNode.getObjectKey(hierarchy_level) + " has not been found in network!")
        return False
    #endif

    if verbose:
        print("\n-- Candidate goal nodes are as follows:")
        for G in goals:
            G.print_functions[hierarchy_level-1]()
    
    print("\n-- Proceeding with task tree retrieval for " + goalNode.getObjectKey(hierarchy_level) + "...")
    goalNode.print_functions[hierarchy_level-1]()
    print()

    possible_kitchen_items = _abstractObjects(environment)

    startNodes = []
    for T in possible_kitchen_items:
        index = -1
        for N in FOON_nodes_compressed:
            if isinstance(N, FOON.Object):
                if T.equals_lvl1(N) and T.isSameStates_ID_only(N):
                    index = FOON_nodes_compressed.index(N)
                    break

        if index != -1:
            # -- this means that the object exists in FOON; if not..
            startNodes.append(FOON_nodes_compressed[index])


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

        depth = frt.depth 	# -- maximum number of times you can "see" the original goal node.
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
# \end{FOON-GEN}


# \begin{ICRA-18}
def _randomSearchExperiment(percent=0.60, n_trials=2, n_objects=5, hierarchy_level=3, expanded_ConceptNet=None, expanded_WordNet=None):
    print(' -- Starting random search experiment...')

    global verbose
    if verbose:
        print('  -- trials = ' + str(n_trials))
        print('  -- n_objects = ' + str(n_objects))
        print('  -- subset = ' + str(percent))

    # First, create random subsets of kitchen items available to the algorithm:
    file = input('  -- Please provide the name of the file with KITCHEN ITEMS (press ENTER ONLY to use default): > ')
    if file == '':
        environment = _identifyKitchenItems() # -- use default 'FOON-input_only_nodes.txt'
    else:
        environment = _identifyKitchenItems(file) # -- use a different text file with kitchen items
    #endif

    if verbose:
        print(' -- Kitchen file provided with ' + str(len(environment)) + ' objects!')

    # -- making use of native Python random library to derive random subsets of objects (both GOALS and KITCHEN):
    import random

    # -- create kitchens for each trial of the searching experiment:
    trial_kitchens = []
    subset_size = int(percent * len(environment))	 # -- size of the subset of ingredients for a particular trial
    print('  -- Kitchen file provided with ' + str(len(environment)) + ' objects!')

    for K in range(n_trials):
        # -- use random.sample() to generate random subsets of a given length:
        # Source: https://www.geeksforgeeks.org/python-random-sample-function/
        #	This is being used to generate a random list of goal nodes for the experiment:
        if verbose:
            print(' -- Random sample ' + str(K) + '/' + str(n_trials))
        trial_kitchens.append( random.sample(environment, subset_size) )

    # -- use random.sample() to generate random subsets of a given length:
    #	This is being used to generate a random list of goal nodes for the experiment:
    goal_nodes = random.sample( _findNodes_OutputOnly(), n_objects)

    # -- now that we have the random subset of goal nodes and the random kitchen subsets, we can proceed 
    #	with the experiments:
    avg_fails_REG = 0; avg_fails_EXP_W = 0; avg_fails_EXP_C = 0; avg_fails_GEN = 0	# -- counting the number of failures from search

    print('\n -- Performing random search on FOON-REG..')
    time_taken = 0	# -- when conducting the search, we need to note the amount of time taken on average..
    for T in range(n_trials):
        n_fails_REG = 0
        for O in range(n_objects):
            # -- get one of the random goal nodes from the list..
            temp_goal = goal_nodes[O]
            start_time = time.time()
            # -- perform search and note whether it is success or not:
            if not _taskTreeRetrieval_greedy(temp_goal.getObjectType(), temp_goal.getStateIDs(), hierarchy_level, environment=trial_kitchens[T]):
                n_fails_REG += 1
            #endif
            end_time = time.time()
            # -- add the time taken to variable:
            time_taken += (end_time - start_time)
        #endfor
        print('  -- trial #' + str(T+1) + ' : ' + str(n_objects - n_fails_REG)  + '/' + str(n_objects))
        avg_fails_REG += n_fails_REG
    #endfor

    avg_time_REG = time_taken / (n_trials * n_objects)

    # -- we will compare both WordNet and Concept-Net approaches:
    print('\n -- Performing random search on FOON-EXP (WordNet)..')
    global object_similarity_index

    if not expanded_WordNet:
        # NOTE: we can do this to avoid having to wait to provide input..
        expanded_WordNet = input("  -- Please enter the name of the EXPANDED FOON you wish to use: (press ENTER when done)> ")
    if os.path.exists(expanded_WordNet) is False:
        # -- executing pre-expansion methods:
        params = _prepareExpansion()
        expanded_WordNet = _expandNetwork_TextBased(object_similarity_index, method=params[0], threshold=params[1], custom_list=params[2])
    # -- using the newly expanded file, we read it as regular FOON file:
    _constructFOON(file=expanded_WordNet)
    _buildInternalMaps()

    time_taken = 0	# -- when conducting the search, we need to note the amount of time taken on average..
    for T in range(n_trials):
        n_fails_EXP = 0
        for O in range(n_objects):
            # -- get one of the random goal nodes from the list..
            temp_goal = goal_nodes[O]
            start_time = time.time()
            # -- perform search and note whether it is success or not:
            if not _taskTreeRetrieval_greedy(temp_goal.getObjectType(), temp_goal.getStateIDs(), hierarchy_level, environment=trial_kitchens[T]):
                n_fails_EXP += 1
            #endif
            end_time = time.time()
            # -- add the time taken to variable:
            time_taken += (end_time - start_time)
        #endfor
        print('  -- trial #' + str(T+1) + ' : ' + str(n_objects - n_fails_EXP)  + '/' + str(n_objects))
        avg_fails_EXP_W += n_fails_EXP
    #endfor

    avg_time_EXP_W = time_taken / (n_trials * n_objects)

    _resetFOON(reload=True)

    print('\n -- Performing random search on FOON-EXP (Concept-Net)..')

    if not expanded_ConceptNet:
        # NOTE: we can do this to avoid having to wait to provide input..
        expanded_ConceptNet = input("  -- Please enter the name of the EXPANDED FOON you wish to use: (press ENTER when done)> ")
    if os.path.exists(expanded_ConceptNet) is False:
        # -- executing pre-expansion methods:
        params = _prepareExpansion()
        expanded_ConceptNet = _expandNetwork_TextBased(object_similarity_index, method=params[0], threshold=params[1], custom_list=params[2])
    # -- using the newly expanded file, we read it as regular FOON file:
    _constructFOON(file=expanded_ConceptNet)
    _buildInternalMaps()

    time_taken = 0	# -- when conducting the search, we need to note the amount of time taken on average..
    for T in range(n_trials):
        n_fails_EXP = 0	
        for O in range(n_objects):
            # -- get one of the random goal nodes from the list..
            temp_goal = goal_nodes[O]
            start_time = time.time()
            # -- perform search and note whether it is success or not:
            if not _taskTreeRetrieval_greedy(temp_goal.getObjectType(), temp_goal.getStateIDs(), hierarchy_level, environment=trial_kitchens[T]):
                n_fails_EXP += 1
            #endif
            end_time = time.time()
            # -- add the time taken to variable:
            time_taken += (end_time - start_time)
        #endfor
        print('  -- trial #' + str(T+1) + ' : ' + str(n_objects - n_fails_EXP)  + '/' + str(n_objects))
        avg_fails_EXP_C += n_fails_EXP
    #endfor

    avg_time_EXP_C = time_taken / (n_trials * n_objects)

    _resetFOON(reload=True)

    print('\n -- Performing random search on FOON-GEN..')
    # NOTE: first check if FOON-GEN and FOON-GEN have been constructed:
    if not FOON_functionalUnits_compressed:
        _constructFOON_GEN()

    time_taken = 0	# -- when conducting the search, we need to note the amount of time taken on average..
    for T in range(n_trials):
        n_fails_GEN = 0
        for O in range(n_objects):
            # -- get one of the random goal nodes from the list..
            temp_goal = goal_nodes[O]
            start_time = time.time()
            # -- perform search and note whether it is success or not:
            if not _taskTreeRetrieval_GEN(temp_goal.getObjectType(), temp_goal.getStateIDs(), environment=trial_kitchens[T]):
                n_fails_GEN += 1
            #endif
            end_time = time.time()
            # -- add the time taken to variable:
            time_taken += (end_time - start_time)
        #endfor
        print('  -- trial #' + str(T+1) + ' : ' + str(n_objects - n_fails_GEN)  + '/' + str(n_objects))
        avg_fails_GEN += n_fails_GEN
    #endfor

    avg_time_GEN = time_taken / (n_trials * n_objects)

    print('\n -- Results of experiment are as follows:')

    print(' ---- AVERAGE PERFORMANCE (SUCCESSES) ----')
    print('\t\tFOON-REG\t\t- ' + str((n_objects * n_trials) - avg_fails_REG))
    print('\t\tFOON-EXP (WordNet)\t- ' + str((n_objects * n_trials) - avg_fails_EXP_C))
    print('\t\tFOON-EXP (Concept-Net)\t- ' + str((n_objects * n_trials) - avg_fails_EXP_C))
    print('\t\tFOON-GEN\t\t- ' + str((n_objects * n_trials) - avg_fails_GEN))

    print(' ---- AVERAGE PERFORMANCE (TIME) ----')
    print('\t\tFOON-REG\t\t- ' + str(avg_time_REG))
    print('\t\tFOON-EXP (WordNet)\t- ' + str(avg_time_EXP_W))
    print('\t\tFOON-EXP (Concept-Net)\t- ' + str(avg_time_EXP_C))
    print('\t\tFOON-GEN\t\t- ' + str(avg_time_GEN))

    input('  -- Press ENTER to continue...')
#enddef

  
# \end{ICRA-18}

###############################################################################################################################

def _start():

    def _printArgumentsUsage():
        print("ERROR: Unrecognized arguments given to script! Please use from one of the following:")
        print(" --help\t\t\t:- gives an overview of all the flags that work with the program")
        print(" --file='X.txt'\t\t:- open FOON file given as 'X.txt', where X can be any given name")
        print(" --verbose (or --v)\t:- this flag turns on verbose mode, which will result in MANY print-outs for debugging the program")
        print(" --expansion\t\t:- this indicates that you wish to perform expansion (NOTE: must be accompanied by the '--model=' and '--threshold=' arguments)")
        print(" --model=X\t\t:- this indicates which model to use for expansion: 1) WordNet (WN), 2) Concept-Net (CN), 3) spaCy (SP) (default: spaCy)")
        print(" --threshold=X\t\t:- this indicates a decimal value from 0 to 1 to determine whether objects are similar (default: 0.9)")
        print(" --compression\t\t:- this indicates that you wish to perform compression (NOTE: must have 'FOON_categories.json' available)")
    #enddef

    try:
        opts, _ = getopt.getopt( sys.argv[1:], 
                    'v:fi:h:exp:mod:thr:com:', 
                    ['verbose',     # -- verbose equals more print statements
                    'file=',        # -- name of the FOON file that will be used for compression/expansion
                    'help',         
                    'expansion',    # -- flag to indicate that expansion will be done
                    "model=",       # -- the type of model that should be used to measure similarity
                    "threshold=",   # -- the threshold value (decimal) that should be met for two objects/words to be similar
                    "compression"   # -- flag to indicate that compression will be done
                    ] )	
    except getopt.GetoptError:
        _printArgumentsUsage(); exit()
    #end

    global verbose, file_name

    generalization_method = 1   # NOTE: 1 -- expansion, 2 -- compression
    
    global expansion_threshold, expansion_model

    global last_updated; print("< fgen: FOON_generalization - (last updated " + str(last_updated) + " ) >")

    print(' -- [FOON-gen] : Provided the following arguments:')

    for opt, arg in opts:
        if opt in ('-v', '--verbose') or opt in ('-v', '--v'):
            print("   -- selected verbose option...")
            verbose = True

        elif opt in ('-fi', '--file'):
            file_name = arg
            if file_name:
                print("   --file:'" + str(file_name) + "'")

        elif opt in ('-exp', '--expansion'):
            generalization_method = 1
            print('   -- generalization method: expansion')

        elif opt in ('-com', '--compression'):
            generalization_method = 2
            print('   -- generalization method: compression')

        elif opt in ('-mod', '--model'):
            # NOTE: must be used in conjunction with '--expansion' flag:
            if arg == 'WN':
                expansion_model = 'WordNet' 
            elif arg == 'CN':
                expansion_model = 'Concept-Net'
            else:
                expansion_model = 'spacy'
    
            if generalization_method == 1:
                print('   -- model for similarity metrics: ' + expansion_model)

        elif opt in ('-mod', '--threshold'):
            # NOTE: must be used in conjunction with '--expansion' flag:
            expansion_threshold = float(arg)

            if generalization_method == 1:
                    print('   -- similarity threshold: ' + str(expansion_threshold))

        else:
            _printArgumentsUsage(); exit()
        #end
    #endfor

    try:
        import FOON_graph_analyser as fga
    except ImportError:
        print(" -- ERROR: Missing FGA (FOON_graph_analyzer.py) file!")
        print("\t-- Download here: https://github.com/davidpaulius/foon_api/src/master/")
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

    # -- use FGA to load the FOON subgraph file, build dictionaries for faster searching, and read index files for labels:
    fga._constructFOON(file_name)

    fga.flag_buildObjectToUnitMap = True
    fga.flag_buildFunctionalUnitMap = True
    fga._buildInternalMaps()

    fga._readIndexFiles()

    _copyDicts({'fu_list' : fga.FOON_functionalUnits, 
            'nodes_list' : fga.FOON_nodes, 
            'outputs_to_fu' : fga.FOON_outputsToUnits, 
            'objs_to_fu' : fga.FOON_objectsToUnits, 
            'fu_to_fu' : fga.FOON_functionalUnitMap,
            'labels' : fga.FOON_labels,
            'obj_senses' : fga.FOON_objectSenses} )

    _startGeneralization({'method': generalization_method, 
                            'model': expansion_model, 
                            'threshold' : expansion_threshold})
    
#enddef

if __name__ == '__main__':
    _start()