# FOON_API: Code for Processing FOON! #

This repository contains code for processing [FOON](https://www.foonets.com) (short for the **functional object-oriented network**) graphs. FOON was developed by the [USF Robot Perception and Action Lab](https://rpal.cse.usf.edu).

Here, you will find several scripts that are needed to operate on FOON files, which are mainly subgraph files as text files (.TXT), .JSON, or, more recently, .PKL files.
Examples of subgraphs can be found in the ``FOON-111/`` directory found in this repository.

Subgraphs can be visualized using the [FOON_view](https://davidpaulius.github.io/foon_view/) tool.

## License

>This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
>
>This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
>
>You should have received a copy of the GNU General Public License along with this program. If not, see https://www.gnu.org/licenses/.


## **Prerequisites**

#### I. General-Purpose :
* [Python 3](https://www.python.org/download/releases/3.0/) (since Python 2 will soon be deprecated)
* [TQDM](https://github.com/tqdm/tqdm) (simply for progress viewing)

#### II. Network Analysis :
* [NumPy](https://numpy.org/install/) - used for finding eigenvalues and eigenvectors for centrality measurements

#### III. FOON Semantic Generalization (read more [here](https://ieeexplore.ieee.org/abstract/document/8460200/)) :
* [NLTK](http://www.nltk.org/howto/wordnet.html) - specifically WordNet Corpus; NLTK is used for word similarity measurements and lemmatization. 
* [gensim](https://radimrehurek.com/gensim/) and [Concept-Net](http://blog.conceptnet.io/word-embeddings/) word embeddings file (if using Concept-Net)


### Overview of Python Scripts

There are two main files needed for general usage of FOON subgraph files, which are:

1. **FOON_graph_analyser.py** - main script containing all operations on FOON files, including but not limited to reading files, merging subgraphs, task tree retrieval, and network centrality analysis
2. **FOON_classes.py** - file containing all class definitions used

The code is written with an object-oriented approach in mind, since a FOON is comprised of nodes that have overlapping features and structures that can take advantage of features and member functions / variables to perform.

See below for more details!

---

## FOON_graph_analyser.py : Main Script for Processing FOON files

### Overview

This script (abbreviated as *FGA*) contains the main program for FOON graph analysis, task planning through task tree retrieval, FOON generalization, and several other smaller operations. 

#### Arguments for Script

To run this program, you will either need to specific the subgraph or universal FOON (either as .TXT or .JSON) that you are trying to open as a program argument (using the *--file=* flag) or you will need to specify the path of the file explicitly. We are currently working on a configuration file that is loaded and used to load this argument and more.

There are other optional flags such as:

1. *--verbose* or *--v* -- turns on verbose mode (NOTE: it will show a lot of output!)

2. *--object=* -- provides an object ID that will be used as a goal for task tree retrieval

3. *--state=[...]* -- provides an object's state ID(s) that will be used as a goal for task tree retrieval in the form of a list (e.g. [1, 2] for state IDs 1 and 2).

Here is an overview of how you would run it:

```
>> python FOON_graph_analyzer.py --file='example.txt' [ --verbose] [--object=X] [--state=[...] ] [--help]
```

#### Using FGA

Once the file is successfully opened, it is parsed by the program to build the graph internally. This uses the graph definition as defined in the **FOON_classes.py** file, hence why this file must be accompanied with *FGA*. It may take some time to load a graph depending on the number of functional units there are, as internal maps are also created to pre-build relations for the task tree retrieval.

After parsing, you will be presented with several options as a menu.

### Alternative Ways of Using *FGA*

Optionally, you can just load the *FGA* directly in a Python command-line or in your own scripts and call the functions directly from there. However, you would still need to load your subgraph file using the *_constructFOON()* function.

```
import FOON_graph_analyzer as fga

fga._constructFOON(file_name)
...
```

---

## FOON_classes.py : Definition of Object-Oriented Concepts for FOON


This file contains class definitions for several objects that are used to describe a FOON graph. We define a FOON as a network or graph containing nodes, which are all denoted as *Things*, that are connected via edges. 
A *Thing* object can either be an *Object*, which refers to objects that are manipulated in tasks, or a *Motion*, which describes the action that is happening in a manipulation.
A *Thing* object maintains neighbours using adjacency lists.
*Object* nodes and *Motion* nodes that are connected together form what we refer to as a *functional unit*, which is defined as a *FunctionalUnit* object.

When running *FGA*, you must have this file downloaded so that it may import its classes and their methods.

---

## Miscellaneous Files

There are other scripts or files that may be useful to researchers using FOON:

1. **FOON_parser.py** - script used for parsing FOON subgraph files to make sure that they all are consistently labelled. 

2. **FOON_view** - a graph visualization tool created using HTML and JS for viewing FOON graphs. This serves the same purpose as the tool found [here](http://foonets.com/FOON_view/visualizer.html). 

3. **FOON_convert_to_JSON.py** - script used to convert FOON subgraph files as text files to .JSON format. This format also works with the *FOON_graph_analyzer.py* script, and it may be useful for your application.

4. **FOON_video_list.xlsx** - this is an Excel sheet that outlines all of the FOON subgraph video sources from which they can be viewed or downloaded.


## FOON_parser.py : A Script for Parsing and Cleaning FOON Files

This script is used to parse files that contain FOON subgraphs. 

Why do we need to do this? 
This is to correct the identifier numbers that are used in labelling objects/motions/states such that they are all consistent with one another. This is important because all nodes must share the same indexing to create a proper FOON.

### Example of Usage

```
>> python FOON_parser.py --source_dir='path/to/src/files' --target_dir='path/to/save/parsed/files' [--skip_json or --skj] [--skip_cat or --skc] [--skip_index or --ski] [--help]
```

### Instructions

This is used as follows: first, you will need to provide the **source** (path of directory or folder containing UNPARSED files) and **target** (path of directory or folder where PARSED files will be saved) directories either using the prompts in the code or by using command-line arguments (*--source_dir* and *--target_dir* respectively).

After the directories are specified and index files are pre-loaded (or not), let the parser run! The program will read all files found in the source folder, tokenize object, motion, and state labels, save them into lists, and then output revised subgraph files using a sorted index number. The program will also 4 output index files as output: 3 individual text files for objects, motions, and states and 1 .JSON file containing all of the labels categorized by their type.

You have the liberty to use existing index files for objects, motions, and/or states to pre-load labels that will be kept and used forward. If you want to always generate a new set of index files, you can either delete the index files you have or use the flag *--skip_index* or *--ski*.

---

### Need Assistance? Have Questions about our Papers?

Please contact the main developer David Paulius at <davidpaulius@usf.edu> or <dpaulius@cs.brown.edu> or Md Sadman Sakib at <mdsadman@usf.edu>!

---

### If you use our work or dataset, please help others find us by citing our following papers:

>    Paulius, David, Yongqiang Huang, Roger Milton, William D. Buchanan, Jeanine Sam, and Yu Sun. "Functional Object-Oriented Network for Manipulation Learning." In 2016 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS), pp. 2655-2662. IEEE, 2016. [link](https://arxiv.org/abs/1902.01537)

>    Paulius, David, Ahmad B. Jelodar, and Yu Sun. "Functional Object-Oriented Network: Construction and Expansion" In 2018 IEEE International Conference on Robotics and Automation (ICRA), pp. 5935-5941. IEEE, 2018. [link](https://arxiv.org/abs/1807.02189)

>    Paulius, David, Kelvin S. P. Dong, and Yu Sun. "Task Planning with a Weighted Functional Object-Oriented Network" In 2021 IEEE International Conference on Robotics and Automation (ICRA). IEEE, 2021. [link](https://arxiv.org/abs/1905.00502)
