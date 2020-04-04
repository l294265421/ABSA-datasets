# ABSA-datasets
datasets for Aspect-Based Sentiment Analysis and codes for reading them.

## goal
1. Try to collect all ABSA datasets
2. Provide uniform interface to read the datasets
3. Since there are no official train and development splits for most ABSA datasets, we try to provide standard splits for them 

## Supported datasets
### [SemEval-2014 Task 4](http://alt.qcri.org/semeval2014/task4/)
1. SemEval-2014-Task-4-LAPT
2. SemEval-2014-Task-4-REST
### [SemEval-2015 Task 12](http://alt.qcri.org/semeval2015/task12/)
1. SemEval-2015-Task-12-LAPT
2. SemEval-2015-Task-12-REST
3. SemEval-2015-Task-12-HOTEL
### [SemEval-2016 Task 5](http://alt.qcri.org/semeval2016/task5/)
SemEval-2016-Task-5-CH-CAME-SB1
SemEval-2016-Task-5-CH-PHNS-SB1
SemEval-2016-Task-5-LAPT-SB1
SemEval-2016-Task-5-LAPT-SB2
SemEval-2016-Task-5-REST-SB1
SemEval-2016-Task-5-REST-SB2
### [bdci2019]
[bdci2019-internet-news-sa](https://www.datafountain.cn/competitions/350)
[bdci2019-financial-negative](https://www.datafountain.cn/competitions/353)
## [A Challenge Dataset and Effective Models for Aspect-Based Sentiment Analysis](https://www.aclweb.org/anthology/D19-1654/)
MAMSACSA
MAMSATSA
##[nlpcc2012](http://tcci.ccf.org.cn/conference/2012/pages/page04_eva.html) 
nlpcc2012-weibo-sa

## Usage
```Python
from data_adapter.data_object import get_dataset_class_by_name

dataset_name = 'SemEval-2014-Task-4-REST'
dataset = get_dataset_class_by_name(dataset_name)()
```

## Related Repositories
[l294265421/ACSA](https://github.com/l294265421/ACSA)

## Contributions
Feel free to contribute!

You can raise an issue or submit a pull request, whichever is more convenient for you.

## Licence
