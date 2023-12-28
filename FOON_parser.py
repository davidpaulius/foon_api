'''
FOON: Parsing Script (FOON_parser):
        (last updated: 6th December, 2021):
-------------------------------------------
-- Written and maintained by: 
    * Md Sadman Sakib (mdsadman@usf.edu)
    * David Paulius (davidpaulius@usf.edu / dpaulius@cs.brown.edu)
-- Special thanks to undergraduate William David Buchanan for assistance with earlier version.

NOTE: If using this program and/or annotations provided by our lab, please kindly cite our papers
    so that others may find our work:
* Paulius et al. 2016 - https://ieeexplore.ieee.org/abstract/document/7759413/
* Paulius et al. 2018 - https://ieeexplore.ieee.org/abstract/document/8460200/

'''
# NOTE: this script is used for rebuilding index files used for FOON as well as making
#	labels consistent among all subgraph files within a given directory.
# -- Input to this function is simply a path to the folder containing the old, unclean subgraph files.
# -- You may include older index files ('FOON-state_index.txt', 'FOON-motion_index.txt', and 'FOON-state_index.txt') 
# 	to use as base list to be added on.

from __future__ import print_function

import os 
import sys
import json
import getopt
import requests
import tqdm

from datetime import datetime

# -- added NLTK lemmatization process to remove unnecessarily plural words:
lemmatizer = None
try:
    from nltk.stem import WordNetLemmatizer
    lemmatizer = WordNetLemmatizer() 

    from nltk.corpus import wordnet
    
except ImportError:
    print(' -- ERROR: NLTK is not downloaded and available for use!')
    print("\t-- Please install it using 'pip install nltk' and then use 'nltk.download()' from a Python terminal.")
    print("\t-- Refer to <https://www.nltk.org/data.html> for more details.")
    sys.exit()

last_updated = '6th December, 2021'

source_dir = None; target_dir = None

skip_categorization = True	# -- flag used to control prompts for categorization (please see below)

skip_JSON_conversion = False # -- flag to control whether files are also outputted as .JSON

skip_index_check = False

def _check_args():
    global source_dir, target_dir, skip_categorization, skip_JSON_conversion, skip_index_check
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'src:tgt:skj:skc:ski:h', ['source_dir=', 'target_dir=', 'skip_json', 'skj', 'skip_cat', 'skc', 'ski', 'skip_index', 'help'])

        if opts:
            print(' -- Provided the following arguments to parser:')

        for opt, arg in opts:
            if opt in ('-src', '--source_dir'):
                print("  -- Unparsed files will be found in '" + str(arg) + "'")
                source_dir = arg
            elif opt in ('-tgt', '--target_dir'):
                print("  -- Parsed files will be stored in '" + str(arg) + "'")
                target_dir = arg
            elif opt in ('-skj', '--skip_json') or opt in ('-skj', '--skj'):
                print('  -- Skipping JSON conversion...')
                skip_JSON_conversion = True
            elif opt in ('-skc', '--skip_cat') or opt in ('-skc', '--skc'):
                print('  -- Skipping FOON categorization...')
                skip_categorization = True
            elif opt in ('-ski', '--skip_index') or opt in ('-ski', '--ski'):
                print('  -- Skipping loading of pre-existing index files...')
                skip_index_check = True
            else:
                _usage()
    except getopt.GetoptError:
        _usage(); sys.exit(2)
#enddef

def _usage():
    print("ERROR: incorrect arguments given to program!")
    print(" --source_dir=""XXX""\t-\tparse files found in path/directory 'XXX'")
    print(" --target_dir=""YYY""\t-\tstore parsed files in path/directory 'YYY'")
    print(" --skip_json / --skj\t-\tskip JSON conversion when parsing all files (omit if you want JSON files)")
#enddef

def _run_parser():
    print('-- [FOON_parser] : Initiating parsing procedure!')

    # -- use the defined variables as on the higher scope:
    global source_dir, target_dir

    if not source_dir:
        source_dir = input(' -- Enter path to directory / location of UNPARSED files: > ')

    if not target_dir:
        target_dir = input(' -- Enter path to directory / location where PARSED files will be saved to: > ')

    print()

    # -- First, list all files within a certain folder:
    file_list = os.listdir(source_dir)

    # NOTE: after each completed parsing session, the date is added to the index files:
    # file_end = '-updated_' + datetime.today().strftime('%d.%m.%Y') + '.txt'

    objectIndex = []; motionIndex = []; stateIndex = []

    object_IDs = {}; state_IDs = {}; motion_IDs = {}

    # NOTE: these structures are used to hold meaning behind the objects or
    # -- we note the object label's sense (or meaning) based on WordNet (if it exists in WordNet, i.e.).
    # -- we also note the motion's categorization based on three types: 1) location-critical motions, 2) state-critical, and 3) time-critical.
    object_senses = {}; motion_categories = {}

    # NOTE: sometimes, the lemmatization messes up valid object names, so we will define an exceptions file that will
    #	list all object labels that should be kept as-is or enforced:
    exceptions = {}

    # NOTE: to make it easier to add new objects, motions, and states, the parser script will attempt to pre-load existing index files.
    # -- the reason for this is that the parsing will create index files based SOLELY on the provided un-parsed files if no file is provided
    #	or found in the directory of this script.

    global skip_categorization, skip_JSON_conversion, skip_index_check

    if not skip_index_check:
        # -- first, attempt to load the combined .JSON index file:
        try:
            _file = open('FOON_index.json', 'r')
            index_file = json.load(_file)
            print(" -- [FOON_parser] : Loaded existing 'FOON_index.json' file!")

            # NOTE: extract object labels from the index file:
            _objects = index_file['objects'] if 'objects' in index_file else []
            for O in _objects:
                object_label = str(O)
                object_ID = int(index_file['objects'][O]['id']) 

                # NOTE: *if present*, sense IDs that are integers refer to Wordnet and sense ID 'C' refers to representation found in Concept-Net:
                object_sense = None
                if 'sense' in index_file['objects'][O]:
                    object_sense = int(index_file['objects'][O]['sense']) if str(index_file['objects'][O]['sense']).isdigit() else index_file['objects'][O]['sense']

                objectIndex.append(object_label)
                object_IDs[object_label] = object_ID
                if object_sense:
                    object_senses[object_label] = object_sense
            #endfor

            # NOTE: extract motion labels from the index file:
            _motions = index_file['motions'] if 'motions' in index_file else []
            for M in _motions:
                motion_label = str(M)
                motion_ID = int(index_file['motions'][M]['id'])
                
                motionIndex.append(motion_label)
                motion_IDs[motion_label] = motion_ID

                # NOTE: some motions may be categorized or assigned to motion classes:
                if 'motion_type' in index_file['motions'][M]:
                    motion_categories[motion_label] = str(index_file['motions'][M]['motion_type'])

            # NOTE: extract state labels from the index file:
            _states = index_file['states'] if 'states' in index_file else []
            for S in _states:
                state_label = str(S)
                state_ID = int(index_file['states'][S]['id'])
                stateIndex.append(state_label)
                state_IDs[state_label] = state_ID

        except FileNotFoundError:

            # NOTE: it will reach here if the .JSON file does not exist.
            # -- in that case, try to load regular .TXT index files:

            try:
                # NOTE: if you want to pre-load an existing 'FOON-state_index.txt' (that also includes 
                # 	objects NOT LIMITED TO those in the subgraphs), this is where it will look for it:
                object_file = open('FOON-object_index.txt', 'r')
                print("-- WARNING: 'FOON_index.json' file not found!")
                print(" -- Loading legacy index files (i.e. text files)...")
                print("-- Loaded 'FOON-object_index.txt' file!")
                for line in object_file:
                    line = line.split("\t")

                    object_label = line[1].lower().rstrip()
                    objectIndex.append(object_label)

                    object_ID = int(line[0]) if line[0].isdigit() else line[0]
                    object_IDs[object_label] = object_ID

                    # NOTE: this refers to the sense for the word in WordNet:
                    if len(line) > 2:
                        # -- a sense will define the MOST appropriate meaning for the object, 
                        object_senses[object_label] = int(line[2].rstrip())
                    else:
                        # -- by default, we will just use the first (usually only) sense of the word:
                        object_senses[object_label] = 1
                    #endif
                #endfor

            except FileNotFoundError:
                print(' -- WARNING: No objects index file located! This means that all objects will be treated as new!')
                pass

            try:
                # NOTE: if you want to pre-load an existing 'motionIndex.txt' (that also includes motion labels 
                # 	NOT LIMITED TO those in the subgraphs), this is where it will look for it:
                motion_file = open('FOON-motion_index.txt', 'r')
                print(" -- [FOON_parser] : Loaded 'FOON-motion_index.txt' file!")
                for line in motion_file:
                    line = line.split("\t")

                    motion_label = line[1].lower().rstrip()
                    motionIndex.append(motion_label)

                    motion_ID = int(line[0])
                    motion_IDs[motion_label] = motion_ID

                    # NOTE: this refers to the motion execution criterion.
                    if len(line) > 2:
                        # -- we can describe motions with the following flags:
                        # 	(L = location-critical, 
                        # 	 S = state-critical,
                        # 	 T = time-critical)
                        motion_categories[motion_label] = str(line[2].rstrip())
                    #endif
                #endfor

            except FileNotFoundError:
                print(' -- WARNING: No motions index file located! This means that all motions will be treated as new!')
                pass

            try:
                # NOTE: if you want to pre-load an existing 'stateIndex.txt' (that also includes state labels 
                # 	NOT LIMITED TO those in the subgraphs), this is where it will look for it:
                _state = open('FOON-state_index.txt', 'r')
                print(" -- [FOON_parser] : Loaded 'FOON-state_index.txt' file!")
                for line in _state:
                    line = line.split("\t")
                    state_label = line[1].lower().rstrip()
                    stateIndex.append(state_label)

                    state_ID = int(line[0])
                    state_IDs[state_label] = state_ID

            except FileNotFoundError:
                print(' -- WARNING: No states index file located! This means that all states will be treated as new!')
                pass
        #end
    #endif

    # NOTE: lemmatization can often times be erroneous, so we will define a file that contains certain
    #		object listings as the name they SHOULD have even after lemmatization: 
    try:
        path, _ = os.path.split(os.path.realpath(__file__))
        except_file = open(os.path.join(path, 'FOON_parser.exceptions'), 'r')
        print(" -- Loaded parser object exceptions file!")
        for line in except_file:
            if line.startswith('#'):
                continue

            line = line.split("\t")
            exceptions[str(line[0]).rstrip()] = str(line[1]).rstrip()

    except FileNotFoundError:
        pass
    #end

    print('\n -- [FOON_parser] : Commencing parsing...')

    for F in file_list:
        if 'index' in str(F).lower() or '.txt' not in str(F).lower():
            # -- skip any files that are really index files:
            continue

        if os.path.isdir(os.path.join(source_dir, F)):
            # -- check if a file is actually a folder:
            continue

        print("  -- parsing '" + str(F) + "'...")

        unparsed_file = open(os.path.join(source_dir, F), "r")
        file_lines = unparsed_file.readlines()

        # Iterate through FOON files to find objects, states, identifiers, and motions.
        for line in file_lines:
            if line.startswith("/") or line.startswith("#"):
                continue

            label = [x for x in line.split("\t") if x != '\n']

            if len(label) < 2:
                print('   -- WARNING: there is a possible mistake with this file:')
                print('\tline ' + str(file_lines.index(line)) + '\t-\t' + str(label))
                continue

            label[1] = label[1].lower().rstrip()

            if line.startswith("O"):
                if len(line.split('\t')) < 3:
                    print('   -- ERROR: there is a mistake with this file:')
                    print('\tline ' + str(file_lines.index(line)) + '\t-\t' + line)
                    sys.exit(0)

                object_label = label[1]

                if lemmatizer:
                    # -- use NLTK.WordNetLemmatizer to lemmatize:
                    object_label = lemmatizer.lemmatize(object_label, pos='n')

                if object_label in exceptions:
                    # -- make the right substitution for the object to correct and override the lemmatization
                    #	(e.g. change 'fry' to 'french fries', as they have completely different meanings):
                    object_label = exceptions[object_label]
                
                if object_label in objectIndex:
                    continue
                else:
                    objectIndex.append(object_label)

                    # NOTE: now we will look for words that share a similar meaning and assign them all the same object ID:
                    new_word = str(object_label).replace(' ', '_')

                    synonym_found = False

                    # -- start with WordNet; look up synsets (also known as synonym rings), which group similar words together:
                    for syn in wordnet.synsets(new_word):
                        # -- check if any synonyms are found in the object index already:
                        if 'food' in syn.lexname() or 'plant' in syn.lexname() or 'substance' in syn.lexname() or 'artifact' in syn.lexname():
                            for lemma in syn.lemmas():
                                word = str(lemma.name()).replace('_', ' ')
                                if word in object_IDs:
                                    print('\t - [WRD] Words found in same synset: ' + object_label + ', ' + word)
                                    object_IDs[object_label] = object_IDs[word]
                                    # -- now that we have found a common word, just continue with parsing..
                                    synonym_found = True
                                    break

                    # -- continue to next line if found:
                    if synonym_found:
                        continue

                    # -- if we do not find a synonym for this word in WordNet, we then try to use Concept-Net:
                    #	refer to Concept-Net API for more details: <https://github.com/commonsense/conceptnet5/wiki/API>

                    # -- first, check for all r/Synonym relations:
                    query_synonyms = requests.get('http://api.conceptnet.io/query?node=/c/en/' + new_word + '&rel=/r/Synonym&other=/c/en').json()

                    if 'edges' in query_synonyms:
                        # -- this REST API query will return results as a JSON, whose edges will list any results found:
                        for syn in query_synonyms['edges']:
                            # -- the synonym for the new label (<new_word>) will be mapped to 'start' position:
                            if syn['start']['label'] in object_IDs:
                                print('\t - [CON:r/Synonym] Words found in same synset: ' + object_label + ', ' + str(syn['start']['label']))
                                object_IDs[object_label] = object_IDs[syn['start']['label']]
                                # -- now that we have found a common word, just continue with parsing..
                                synonym_found = True
                                break

                    # -- continue to next line if found:
                    if synonym_found:
                        continue

                    # -- if nothing found from r/Synonym relations, then we can try r/InstanceOf, which also tells us certain objects 
                    # 	that can be considered as others (e.g. naan can be considered as an instance of bread):
                    query_instanceof = requests.get('http://api.conceptnet.io/query?node=/c/en/' + new_word + '&rel=/r/InstanceOf&other=/c/en').json()

                    if 'edges' in query_instanceof:
                        # -- this REST API query will return results as a JSON, whose edges will list any results found:
                        for syn in query_instanceof['edges']:
                            # -- the synonym for the new label (<new_word>) will be mapped to 'start' position:
                            if syn['start']['label'] in object_IDs:
                                print('\t - [CON:r/InstanceOf] -- Words found in same synset: ' + object_label + ', ' + str(syn['start']['label']))
                                object_IDs[object_label] = object_IDs[syn['start']['label']]
                                # -- now that we have found a common word, just continue with parsing..
                                synonym_found = True
                                break

                    # -- continue to next line if found:
                    if synonym_found:
                        continue

                    # -- if synonym searching fails, then just add the object label as a new item;
                    #	this is the case with many labels for mixtures, certain goal nodes, etc.
                    object_IDs[object_label] = len(objectIndex) - 1

            elif line.startswith("S"):
                # NOTE: check the state line for the second (i.e. actual state label) and third entry (i.e. ingredients / state relater):

                state_label = label[1]
                if lemmatizer:
                    # -- checking state label after lemmatization:
                    state_label = lemmatizer.lemmatize(state_label)

                if state_label in stateIndex:
                    pass
                else:
                    # -- just add states as we see them:
                    stateIndex.append(state_label)
                    state_IDs[state_label] = len(stateIndex) - 1
                #endif

                if len(label) > 2:
                    # NOTE: check the ingredients or state relater labels, which should also be parsed:

                    # -- this label is the third item of the state's line:
                    unparsed_relation = label[2].rstrip()

                    objects_to_review, unparsed_objects = [], []

                    # -- compile a list of all the ingredients that were found on the line:
                    if '[' in unparsed_relation and ']' in unparsed_relation:
                        unparsed_objects = [ unparsed_relation.split('[')[1].split(']')[0] ]

                    elif '{' in unparsed_relation and '}' in unparsed_relation:
                        unparsed_objects = unparsed_relation.split('{')[1].split('}')[0].split(',')
                    else:
                        print('   -- ERROR: there is an issue here with this line:')
                        print('\tline ' + str(file_lines.index(line)) + '\t-\t' + str(label))
                        sys.exit(0)

                    for obj in unparsed_objects:
                        object_label = obj
                        if lemmatizer:
                            # -- use NLTK.WordNetLemmatizer to lemmatize:
                            object_label = lemmatizer.lemmatize(obj, pos='n')

                        # -- check exceptions file for any substitutions that should be made:
                        if object_label in exceptions:
                            object_label = exceptions[object_label]

                        objects_to_review.append(object_label)

                    # -- repeating same synonym searching process as we have done before for objects:
                    for obj in objects_to_review:
                        if obj in objectIndex:
                            continue

                        else:
                            # -- make the right substitution for the object to correct the lemmatization
                            #	(e.g. change 'fry' to 'french fries', as they have completely different meanings):
                            objectIndex.append(obj)

                            # NOTE: now we will look for words that share a similar meaning and assign them all the same object ID:
                            new_word = str(obj).replace(' ', '_')

                            synonym_found = False

                            # -- start with WordNet; look up synsets (also known as synonym rings), which group similar words together:
                            for syn in wordnet.synsets(new_word):
                                # -- check if any synonyms are found in the object index already:
                                if 'food' in syn.lexname() or 'plant' in syn.lexname() or 'substance' in syn.lexname() or 'artifact' in syn.lexname():
                                    for lemma in syn.lemmas():
                                        word = str(lemma.name()).replace('_', ' ')
                                        if word in object_IDs:
                                            print('\t - [WRD] Words found in same synset: ' + obj + ', ' + word)
                                            object_IDs[obj] = object_IDs[word]
                                            # -- now that we have found a common word, just continue with parsing..
                                            synonym_found = True
                                            break

                            # -- continue to next line if found:
                            if synonym_found:
                                continue

                            # -- if we do not find a synonym for this word in WordNet, we then try to use Concept-Net:
                            #	refer to Concept-Net API for more details: <https://github.com/commonsense/conceptnet5/wiki/API>
                            query_synonyms = requests.get('http://api.conceptnet.io/query?node=/c/en/' + new_word + '&rel=/r/Synonym&other=/c/en').json()

                            # -- this REST API query will return results as a JSON, whose edges will list any results found:
                            for syn in query_synonyms['edges']:
                                # -- the synonym for the new label (<new_word>) will be mapped to 'start' position:
                                if syn['start']['label'] in object_IDs:
                                    print('\t - [CON:r/Synonym] Words found in same synset: ' + obj + ', ' + str(syn['start']['label']))
                                    object_IDs[obj] = object_IDs[syn['start']['label']]
                                    # -- now that we have found a common word, just continue with parsing..
                                    synonym_found = True
                                    break

                            # -- continue to next line if found:
                            if synonym_found:
                                continue

                            # -- if nothing found from r/Synonym relations, then we can try r/InstanceOf, which also tells us certain objects 
                            # 	that can be considered as others (e.g. naan can be considered as an instance of bread):
                            query_instanceof = requests.get('http://api.conceptnet.io/query?node=/c/en/' + new_word + '&rel=/r/InstanceOf&other=/c/en').json()

                            # -- this REST API query will return results as a JSON, whose edges will list any results found:
                            for syn in query_instanceof['edges']:
                                # -- the synonym for the new label (<new_word>) will be mapped to 'start' position:
                                if syn['start']['label'] in object_IDs:
                                    print('\t - [CON:r/InstanceOf] Words found in same synset: ' + object_label + ', ' + str(syn['start']['label']))
                                    object_IDs[object_label] = object_IDs[syn['start']['label']]
                                    # -- now that we have found a common word, just continue with parsing..
                                    synonym_found = True
                                    break

                            # -- continue to next line if found:
                            if synonym_found:
                                continue

                            # -- if synonym searching fails, then just add the object label as a new item;
                            #	this is the case with many labels for mixtures, certain goal nodes, etc.
                            object_IDs[obj] = len(objectIndex) - 1
                #endif

            elif line.startswith("M"):
                if len(line.split('\t')) < 4:
                    if '<' in line and '>' in line:
                        # NOTE: adding new convention of putting times in a universal FOON:
                        pass
                    else:
                        print('   -- ERROR: there is a mistake with this file:')
                        print('\tline ' + str(file_lines.index(line)) + '\t-\t' + line)
                        sys.exit(0)
                    #endif
                #endif

                # -- remove asterisk signifying a composite functional unit:
                label[1] = label[1].replace('*', '')					

                # --  lemmatize based on part-of-speech (in this case, it should be a verb):
                if lemmatizer:
                    # -- use NLTK.WordNetLemmatizer to lemmatize:
                    label[1] = lemmatizer.lemmatize(label[1], pos='v')

                if label[1] in motionIndex:
                    continue
                else:
                    motionIndex.append(label[1])
                    motion_IDs[label[1]] = len(motionIndex) - 1
                #endif

            else:
                pass

        #endfor
    #endfor

    # NOTE: make sure that everything is unique and sorted before beginning!
    objectIndex = sorted(list(set(objectIndex)))
    motionIndex = sorted(list(set(motionIndex)))
    stateIndex = sorted(list(set(stateIndex)))

    print("\n -- [FOON_parser] : Saving corrected files to '" + target_dir + "'...")

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # -- now that we have revised the index files, we will now adjust the labels in the old files:
    for F in file_list:
        if 'index' in str(F).lower() or '.txt' not in str(F).lower():
            # -- skip any files that are really index files:
            continue

        if os.path.isdir(os.path.join(source_dir, F)):
            continue

        unparsed_file = open(os.path.join(source_dir, F), "r")
        parsed_file = open(os.path.join(target_dir, F), 'w')

        unparsed_lines = unparsed_file.readlines()

        print("  -- Saving '" + str(F) + "'...")	

        for line in unparsed_lines:
            if line.startswith("# Source:") or line.startswith('/'):
                # -- new addition: note the source of the annotated video:
                parsed_file.write(line)
                continue

            label = [x for x in line.split("\t") if x != '\n']

            if len(label) < 2:
                # -- this is to make sure that we skip incorrect lines
                print('   -- WARNING: line ' + str(unparsed_lines.index(line)) + ' is possibly incorrect : ' + str(label))
                continue

            parsed_line = ''

            label[1] = label[1].lower().rstrip()

            if line.startswith("O"):
                # NOTE: exclamation part is just simply for the indication of the intended goal:
                object_label = label[1]
                if lemmatizer:
                    object_label = lemmatizer.lemmatize(object_label, pos='n')

                if object_label in exceptions:
                    object_label = exceptions[object_label]

                parsed_line = 'O' + str(object_IDs[object_label]) + '\t' + object_label +  '\t' + str(label[2].rstrip()) + (('\t!') if '!' in line else '') + '\n'

            if line.startswith("S"):
                # -- correcting state label...
                state_label = label[1]
                if lemmatizer:
                    state_label = lemmatizer.lemmatize(state_label)

                if len(label) < 3:
                    parsed_line = 'S' + str(state_IDs[state_label]) + '\t' + state_label + '\n'
                else:
                    unparsed_relation, unparsed_objects = label[2].rstrip(), None
                    # -- compile a list of all the ingredients that were found on the line:
                    if '[' in unparsed_relation and ']' in unparsed_relation:
                        unparsed_objects = [ unparsed_relation.split('[')[1].split(']')[0] ]

                    elif '{' in unparsed_relation and '}' in unparsed_relation:
                        unparsed_objects = unparsed_relation.split('{')[1].split('}')[0].split(',')
                    else:
                        print('   -- ERROR: there is an issue here with this line:')
                        print('\tline ' + str(unparsed_lines.index(line)) + '\t-\t' + str(label))
                        sys.exit(0)
                    #endif

                    # -- checking the (list of) object(s) and rebuild it/them using the corrected labels:
                    state_relation = ''
                    for obj in unparsed_objects:
                        object_label = obj
                        if lemmatizer:
                            # -- use NLTK.WordNetLemmatizer to lemmatize:
                            object_label = lemmatizer.lemmatize(obj, pos='n')

                        # -- check exceptions file for any substitutions that should be made:
                        if object_label in exceptions:
                            object_label = exceptions[object_label]

                        state_relation += object_label + (',' if len(unparsed_objects) != unparsed_objects.index(obj) + 1 else '')

                    # -- make sure to use the right brackets to surround the (list of) object(s):
                    if '[' in unparsed_relation:
                        state_relation = '[' + state_relation + ']'
                    elif '{' in unparsed_relation:
                        state_relation = '{' + state_relation + '}'
                    else:
                        print('   -- ERROR: there is an issue here with this line:')
                        print('\tline ' + str(unparsed_lines.index(line)) + '\t-\t' + str(label))
                        sys.exit(0)
                    #endif

                    parsed_line = 'S' + str(state_IDs[state_label]) + '\t' + state_label + '\t' + state_relation + '\n'

            if line.startswith("M"):
                # -- correcting motion label...
                motion_label = label[1].replace('*', '')

                if lemmatizer:
                    # -- use NLTK.WordNetLemmatizer to lemmatize:
                    motion_label = lemmatizer.lemmatize(motion_label, pos='v')

                if len(label) == 3:
                    # -- this is a line with form: MXXX <name> <start_time,end_time>
                    parsed_line = 'M' + str(motion_IDs[motion_label]) + '\t' + (motion_label + ('*' if '*' in label[1] else '')) + '\t' + label[2].rstrip() + '\n'
                elif len(label) == 4:
                    # -- this is a line with form: MXXX <name> <start_time> <end_time>
                    parsed_line = 'M' + str(motion_IDs[motion_label]) + '\t' + (motion_label + ('*' if '*' in label[1] else '')) + '\t' + label[2] + '\t' + label[3].rstrip() + '\n'
                elif len(label) == 5:
                    # -- this is a line with form: MXXX <name> <start_time,end_time> <entity> <success_rate>
                    parsed_line = 'M' + str(motion_IDs[motion_label]) + '\t' + (motion_label + ('*' if '*' in label[1] else '')) + '\t' + label[2] + '\t' + label[3] + '\t' + label[4].rstrip() + '\n'
                else:
                    # -- this is a line with form: MXXX <name> <start_time> <end_time> <entity> <success_rate>
                    parsed_line = 'M' + str(motion_IDs[motion_label]) + '\t' + (motion_label + ('*' if '*' in label[1] else '')) + '\t' + label[2] + '\t' + label[3] + '\t' + label[4] + '\t' + label[5].rstrip() + '\n'

            parsed_file.write(parsed_line)
        #endfor

        parsed_file.close(); unparsed_file.close()

        # -- if you do not want to keep the unparsed version for record-keeping, you can switch this on the following:

        # replace the unparsed file with the parsed file
        # os.rename(parsed_filepath, unparsed_filepath)

    #endfor

    # NOTE: try using WordNet to guess the appropriate sense of a word, so that the newly updated index 
    #	will reflect these new additions. This should only be done if NLTK and WordNet are available.

    print('\n-- Revising object label senses using WordNet and Concept-Net...\n')

    # -- this can be done to alleviate the need to manually assign all senses

    for O in objectIndex:
        # -- if a word already has a sense assigned to it, then we just skip it:
        if O in object_senses:
            continue

        # -- prepare the object label for analysis with WordNet; change whitespaces to underscores:
        object_name = O.replace(' ', '_')
        object_synsets = wordnet.synsets(object_name)

        # -- by default, use the first sense:
        object_sense = 1

        sense_found = False

        # -- first, check to see if there is a 'food' definition for the object:		
        for synset in object_synsets:
            if 'food' in synset.lexname():
                object_sense = object_synsets.index(synset) + 1
                sense_found = True
                break

        if sense_found:
            object_senses[O] = int(object_sense)
            continue

        for synset in object_synsets:
            if 'plant' in synset.lexname():
                object_sense = object_synsets.index(synset) + 1
                sense_found = True
                break

        if sense_found:
            object_senses[O] = int(object_sense)
            continue

        # -- if there is no food definition, then we can try to see if we can find a 'substance' meaning
        #	(for certain ingredients or liquids):
        for synset in object_synsets:
            if 'substance' in synset.lexname():
                object_sense = object_synsets.index(synset) + 1
                sense_found = True
                break

        if sense_found:
            object_senses[O] = int(object_sense)
            continue

        # -- if there is no food definition, then we can try to see if we can find an 'artifact' meaning
        #	(for utensils, tools or appliances):
        for synset in object_synsets:
            if 'artifact' in synset.lexname():
                object_sense = object_synsets.index(synset) + 1
                sense_found = True
                break

        if sense_found:
            object_senses[O] = int(object_sense)
            continue

        # --  check to see if a word or phrase exists as a concept in Concept-Net:
        try:
            query_concept = requests.get('http://api.conceptnet.io/c/en/' + object_name).json()
            if query_concept['edges']:
                # -- even if we cannot find it in WordNet, we could use Concept-Net to find similarity:
                object_senses[O] = 'C'
        except ConnectionError:
            continue

        # --  if a word was not found, we will not give it a sense number

    #endfor

    print('\nSUMMARY OF CHANGES:')
    print('  -- new total of OBJECTS : ' + str(len(objectIndex)))
    print('  -- new total of STATES : ' + str(len(stateIndex)))
    print('  -- new total of MOTIONS : ' + str(len(motionIndex)))

    if not skip_JSON_conversion:
        print('\n-- Converting all parsed files to .JSON format...')
        convert_to_JSON(target_dir)

    # NOTE: (current idea) create a combined index file that contains objects, motions and states:
    # -- this file will be a .JSON file..
    index_file = {}
    index_file['date_created'] = str(datetime.today().strftime('%d.%m.%Y'))
    index_file['motions'] = {}
    index_file['objects'] = {}
    index_file['states'] = {}

    # -- writing object labels to files..
    parsed_file = open('FOON-object_index.txt', 'w')
    for O in objectIndex:
        # -- writing to .TXT index file:
        if O in object_senses:
            parsed_file.write(str(object_IDs[O]) + "\t" + str(O) + "\t" + str(object_senses[O]) + "\n")
        else:
            parsed_file.write(str(object_IDs[O]) + "\t" + str(O) + "\n")

        # -- writing to .JSON index file:
        index_file['objects'][O] = {}
        index_file['objects'][O]['id'] = object_IDs[O]
        if O in object_senses:
            index_file['objects'][O]['sense'] = object_senses[O]
    #end
    parsed_file.close()

    # -- writing motion labels to files..
    parsed_file = open('FOON-motion_index.txt', 'w')
    for M in motionIndex:
        # -- writing to .TXT index file:
        parsed_file.write(str(motion_IDs[M]) + "\t" + str(M) + (str("\t" + str(motion_categories[M])) if M in motion_categories else str()) + "\n")

        # -- writing to .JSON index file:
        index_file['motions'][M] = {}
        index_file['motions'][M]['id'] = motion_IDs[M]
        if M in motion_categories:
            index_file['motions'][M]['motion_type'] = motion_categories[M]
    #end
    parsed_file.close()

    # -- writing state labels to files..
    parsed_file = open('FOON-state_index.txt', 'w')
    for S in stateIndex:
        parsed_file.write(str(state_IDs[S]) + "\t" + str(S) + "\n")
        index_file['states'][S] = {}
        index_file['states'][S]['id'] = state_IDs[S]
    #end
    parsed_file.close()

    # NOTE: this is the combined index file:
    json.dump(index_file, open('FOON_index.json', 'w'), indent=7, sort_keys=True)

    if exceptions:
        path, _ = os.path.split(os.path.realpath(__file__))
        except_file = open(os.path.join(path, 'FOON_parser.exceptions'), 'w')
        except_file.write('# FOON_parser.py -- Exceptions File\n')
        except_file.write('# -- this file features object label corrections for certain lemmatized words\n')
        except_file.write('# -- format is: <lemmatized_name> \t <corrected_name>\n')
        for obj in exceptions:
            except_file.write(str(obj) + '\t' + str(exceptions[obj]) + '\n')

    # NOTE: this has to do with categories of objects and motions that are used for some of FOON's operations.
    #	however, these are not used for common tasks but rather for things such as FOON task tree retrieval
    #		using concepts of expansion / compression.
    # -- please refer to Paulius et al. 2018 (ICRA 2018) for further explanation on these operations.
    # -- if you do not care about these, you can skip this part and set 'skip_categorization' flag to True.

    if not skip_categorization:
        _response = input('\n -- Create the FOON categories index file? [Y/N] > ')

        if _response == 'y' or _response == 'Y':
            category_index = {}

            category_index['date_created'] = str(datetime.today().strftime('%d.%m.%Y'))

            category_index['object_categories'] = {}

            _response = input('  -- Re-use object categories from previous version (if not, it will create index from legacy file)? [Y/N] > ')

            if _response == 'y' or _response == 'Y':
                # -- try to use existing 'FOON_categories.json' file and build upon it:
                try:
                    _file = open('FOON_categories.json', 'r')
                    categories_file = json.load( _file )
                    category_index['object_categories'] = categories_file['object_categories'] if 'object_categories' in categories_file else {}

                except FileNotFoundError:
                    pass

            else:
                # -- if there is no 'FOON_categories.json' file, then just assume that we have to build from legacy version (.TXT file):

                try:
                    _file = open('object_categories.txt', 'r')

                except FileNotFoundError:
                    pass

                else:
                    items = _file.read().splitlines()
                    
                    for line in items:
                        temp = line.split(":")
                        new_category = temp[0]
                        category_index['object_categories'][new_category] = []
                        temp = temp[1].split(",")
                        # list_categories = []
                        for S in temp:
                            if bool(S):
                                category_index['object_categories'][new_category].append(S)
                            #endif
                        #endfor
                    #endfor
                #end
            #end

            category_index['motion_categories'] = {'location_critical' : [], 'state_critical' : [], 'time_critical' : []}
                
            for _item in motion_categories:
                # NOTE: L - location critical, T - time critical, S - state critical:
                if motion_categories[_item] == 'L':
                    category_index['motion_conditions']['location_critical'].append(_item)
                elif motion_categories[_item] == 'S':
                    category_index['motion_conditions']['state_critical'].append(_item)
                elif motion_categories[_item] == 'T':
                    category_index['motion_conditions']['time_critical'].append(_item)
                else:
                    print(" -- WARNING: incorrect motion criterion flag for motion '" + str(_item) + "'")
                #endif
            #endfor

            category_index['state_taxonomy'] = {}

            _response = input('  -- Re-use state taxonomy from previous version (if not, it will create index from legacy file)? [Y/N] > ')

            if _response == 'y' or _response == 'Y':
                # -- try to use existing 'FOON_categories.json' file and build upon it:
                try:
                    _file = open('FOON_categories.json', 'r')
                    categories_file = json.load( _file )
                    category_index['state_taxonomy'] = categories_file['state_taxonomy'] if 'state_taxonomy' in categories_file else {}

                except FileNotFoundError:
                    pass

            else:
                # -- if there is no 'FOON_categories.json' file, then just assume that we have to build from legacy version (.TXT file):

                try:
                    _file = open('state_taxonomy.txt', 'r')

                except FileNotFoundError:
                    pass

                else:
                    items = _file.read().splitlines()
                        
                    for line in items:
                        temp = line.split(":")
                        new_category = temp[0]
                        category_index['state_taxonomy'][new_category] = []
                        temp = temp[1].split(",")
                        list_categories = []
                        for S in temp:
                            if bool(S):
                                category_index['state_taxonomy'][new_category].append(S)
                            #endif
                        #endfor
                    #endfor
                #end
            #end

            json.dump(category_index, open('FOON_categories.json', 'w'), indent=7)

        #endif
    #endif

    print('\n -- [FOON_parser] : Parsing complete!')
#enddef


def convert_to_JSON(directory=None):
    try:
        import FOON_graph_analyser as fga
        fga.FOON.print_old_style = True
    except ImportError:
        print("ERROR: Missing 'FOON_graph_analyzer.py' file!")
        exit()

    if not directory:
        # -- this means we did not specify the directory before run-time:
        directory = input("-- Please enter the DIRECTORY with files to be converted to .JSON format: > ")

    print("-- Provided directory '" + str(directory) + "'...")
    for root, _, files in os.walk(os.path.abspath(directory)):

        files = [ fi for fi in files if fi.endswith('.txt') ]

        if files:
            if not os.path.exists(os.path.join(os.path.abspath(directory), 'JSON')):
                os.makedirs(os.path.join(os.path.abspath(directory), 'JSON'))

        for file in tqdm.tqdm(files):
            # -- go through each file in the provided directory with FOON subgraph files:
            file_name =  os.path.join(root, file)

            fga._resetFOON()

            # -- use _constructFOON() function as already defined in the graph analyzer code:
            fga._constructFOON(file_name)

            # -- create a dictionary to store each functional unit:
            subgraph_units = {}
            subgraph_units['functional_units'] = []

            for FU in fga.FOON_lvl3:
                # -- use function already defined in FOON_classes.py file:
                subgraph_units['functional_units'].append( FU.getFunctionalUnitJSON() )

            if fga.FOON_video_source:
                subgraph_units['source'] = fga.FOON_video_source

            json_file_name = os.path.splitext(file)[0] + '.json'

            # -- dump all the contents in dictionary as .JSON:
            json.dump(subgraph_units, open(os.path.join(os.path.abspath(directory), 'JSON', json_file_name), 'w'), indent=7)
        #end
    #end

#enddef


if __name__ == '__main__':
    print("< FOON_parser.py (updated " + str(last_updated) + " ) >\n")

    _check_args(); _run_parser()