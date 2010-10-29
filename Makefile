DATASET=${HHOME}/datasets/wikipedia/${LANG}
SOURCE=~/dev/repos/wiki-network

graph:
	cd ${DATASET} ; ${SOURCE}/utpedits2graph.py ${LANG}wiki-${DATE}-${TYPE}.xml.${EXT}

enrich:
	cd ${DATASET} ; ${SOURCE}/graph_enrich.py ${LANG}wiki-${DATE}-${TYPE}.pickle

hist:
	cd ${SOURCE} ; ./graph_analysis.py -c all -g ${DATASET}/${LANG}wiki-${DATE}-${TYPE}_rich.pickle

analysis:
	cd ${SOURCE} ; ./graph_analysis.py --save-db --group -der --distance --power-law ${DATASET}/${LANG}wiki-${DATE}-${TYPE}_rich.pickle

param-analysis:
	cd ${SOURCE} ; ./graph_analysis.py ${PARAMS} ${DATASET}/${LANG}wiki-${DATE}-${TYPE}_rich.pickle


centrality:
	cd ${SOURCE} ; ./graph_analysis.py --save-db --group -c all ${DATASET}/${LANG}wiki-${DATE}-${TYPE}_rich.pickle

all-hist: graph enrich hist

all: graph enrich analysis

test:
	nosetests
