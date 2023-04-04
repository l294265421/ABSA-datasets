"""
该模块提供以下功能：
1. 提供类对各类情感数据集里数据的抽象
2. 提供对加载预定义数据集得到数据集的统一表示的方法
"""

import logging
import os
import json
import re
import csv
import pickle
import sys
from collections import defaultdict
from typing import List

from bs4 import BeautifulSoup
from bs4.element import Tag
from sklearn.model_selection import train_test_split

from common import common_path
from utils import file_utils


logger = logging.getLogger(__name__)
base_data_dir = os.path.join(common_path.project_dir, 'data')


class AspectTerm:
    """
    aspect term
    """

    def __init__(self, term, polarity, from_index, to_index, category=None):
        self.term = term
        self.polarity = polarity
        # inclusive
        self.from_index = int(from_index)
        # exclusive
        self.to_index = int(to_index)
        self.category = category

    def __str__(self):
        return '%s-%s-%s-%s-%s' % (self.term, str(self.polarity), str(self.from_index), str(self.to_index),
                                   self.category)


class AspectCategory:
    """
    aspect category
    """

    def __init__(self, category, polarity):
        self.category = category
        self.polarity = polarity

    def __str__(self):
        return '%s-%s' % (self.category, str(self.polarity))


class Text:
    """
    文本
    """

    def __init__(self, text, polarity, sample_id=''):
        self.text = text
        self.polarity = polarity
        self.sample_id = sample_id

    def __str__(self):
        return '%s-%s' % (self.text, str(self.polarity))


class AbsaText(Text):
    """
    属性级情感分析中的文本
    """

    def __init__(self, text, polarity, aspect_categories, aspect_terms, sample_id=''):
        super().__init__(text, polarity, sample_id=sample_id)
        self.aspect_categories = aspect_categories
        self.aspect_terms = aspect_terms


class AbsaSentence(AbsaText):
    """
    一个句子
    """

    def __init__(self, text, polarity, aspect_categories, aspect_terms, sample_id='', start_index_in_doc=-1):
        super().__init__(text, polarity, aspect_categories, aspect_terms, sample_id=sample_id)
        self.start_index_in_doc = start_index_in_doc


class AbsaDocument(AbsaText):
    """
    一个文档
    """

    def __init__(self, text, polarity, aspect_categories, aspect_terms, absa_sentences, sample_id=''):
        super().__init__(text, polarity, aspect_categories, aspect_terms, sample_id=sample_id)
        self.absa_sentences = absa_sentences

    def get_plain_text_of_sentences(self):
        """

        :return:
        """
        result = []
        if self.absa_sentences is None:
            return result
        for sentence in self.absa_sentences:
            result.append(sentence.text)
        return result


class BaseDataset:
    """
    base class
    memory mirror of datasets
    """

    def __init__(self, configuration: dict=None):
        self.configuration = configuration
        self.train_data, self.dev_data, self.test_data = self._load_data()

    def _load_data(self):
        """
        加载数据
        :return:
        """
        return None, None, None

    def get_data_type_and_data_dict(self):
        data_type_and_data = {
            'train': self.train_data,
            'dev': self.dev_data,
            'test': self.test_data
        }
        return data_type_and_data

    def get_sentences(self, data_type: str):
        """

        :param data_type: train, dev, or test
        :return: all sentences in the specified dataset
        """

        data_type_and_data = self.get_data_type_and_data_dict()
        if data_type is None or data_type not in data_type_and_data:
            logger.info('unknown data type: %s' % str(data_type))
            return []
        data = data_type_and_data[data_type]
        sentences = []
        for document in data:
            for sentence in document.get_plain_text_of_sentences():
                sentences.append(sentence)
        return sentences

    def get_documents(self, data_type: str):
        """

        :param data_type: train, dev, or test
        :return: all sentences in the specified dataset
        """

        data_type_and_data = self.get_data_type_and_data_dict()
        if data_type is None or data_type not in data_type_and_data:
            logger.info('unknown data type: %s' % str(data_type))
            return []
        data = data_type_and_data[data_type]
        documents = []
        for document in data:
            documents.append(document.text)
        return documents

    def generate_atsa_data(self, test_size=0.2):
        """

        :return:
        """
        result = {
            'train': None,
            'dev': None,
            'test': None
        }
        distinct_polarities = set()
        data_type_and_data = self.get_data_type_and_data_dict()
        for data_type, data in data_type_and_data.items():
            if data is None:
                continue
            samples = []
            for document in data:
                for sentence in document.absa_sentences:
                    content = re.sub('[\r\n]', '', sentence.text)
                    # content = re.sub('[\-/]', ' ', content)
                    label = []
                    for aspect_term in sentence.aspect_terms:
                        label.append(aspect_term)
                        polarity = aspect_term.polarity
                        distinct_polarities.add(polarity)
                    samples.append([content, label])
            result[data_type] = samples
        if result['dev'] is None and test_size is not None:
            original_train_samples = result['train']
            train_samples, dev_samples = train_test_split(original_train_samples, test_size=test_size)
            result['train'] = train_samples
            result['dev'] = dev_samples
        distinct_polarities = list(distinct_polarities)
        distinct_polarities.sort()
        return result, distinct_polarities

    def generate_dev_data(self, result, dev_size, random_state=1234):
        """
        当没有官方发布的开发集时，根据指定参数情况生成开发集
        :param result: data_type_and_data
        :param dev_size: 指定的开发集划分比例
        :param random_state:
        :return:
        """

        if result['dev'] is None:
            if dev_size != 0.0:
                original_train_samples = result['train']
                train_samples, dev_samples = train_test_split(original_train_samples, test_size=dev_size,
                                                              random_state=random_state)
                result['train'] = train_samples
                result['dev'] = dev_samples
            else:
                result['dev'] = result['test']


class AsgcnData(BaseDataset):
    """
    Aspect-basedSentimentClassiﬁcationwithAspect-speciﬁcGraph ConvolutionalNetworks

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data_by_filepath(self, train_filepath, test_filepath):
        data_type_and_filepath = {'train': train_filepath,
                                  'test': test_filepath}
        data_type_and_data = {}
        for data_type, filepath in data_type_and_filepath.items():
            lines = file_utils.read_all_lines(filepath)
            sentences = []
            polarity_mapping = {'-1': 'negative',
                                '0': 'neutral',
                                '1': 'positive'}
            for i in range(0, len(lines), 3):
                text_left, _, text_right = [s.lower().strip() for s in lines[i].partition("$T$")]
                aspect = lines[i + 1].lower().strip()
                polarity = lines[i + 2].strip()
                if text_left != '':
                    text = text_left + " " + aspect
                    from_index = len(text_left) + 1
                else:
                    text = aspect
                    from_index = 0
                if text_right != '':
                    text = text + ' ' + text_right
                to_index = from_index + len(aspect)
                if text[from_index: to_index] != aspect:
                    logger.error('error aspect index: %s != %s' (text[from_index: to_index], aspect))
                aspect_term = AspectTerm(aspect, polarity_mapping[polarity], from_index, to_index)
                sentence = AbsaSentence(text, None, None, [aspect_term])
                sentences.append(sentence)
            documents = [AbsaDocument(sentence.text, None, None, None, [sentence]) for sentence in sentences]
            data_type_and_data[data_type] = documents
        return data_type_and_data['train'], None, data_type_and_data['test']


class Nlpcc2012WeiboSa(BaseDataset):
    """

    """

    def __init__(self, configuration):
        super().__init__(configuration)

    def _load_data(self):
        data_dir = os.path.join(base_data_dir, 'NLP-CC2012-微博情感分析评测数据', '微博情感分析评测', '测试数据')
        filenames = os.listdir(data_dir)
        samples = []
        for filename in filenames:
            filepath = os.path.join(data_dir, filename)
            content = file_utils.read_all_content(filepath, encoding='utf-16-le')
            soup = BeautifulSoup(content, "lxml")
            weibo_tags: List[Tag] = soup.find_all('weibo')
            for weibo_tag in weibo_tags:
                weibo_id = weibo_tag.get('id', '')
                sentences: List[AbsaSentence] = []
                sentence_tags: List[Tag] = weibo_tag.find_all('sentence')
                sentence_start_index = 0
                for sentence_tag in sentence_tags:
                    sentence_id = sentence_tag.get('id', '')
                    opinionated = sentence_tag.get('opinionated', '')
                    sentence_polarity = None
                    sentence_text = sentence_tag.get_text()
                    aspect_terms = []
                    if opinionated == 'Y':
                        sentence_polarity = sentence_tag.get('polarity')
                        aspect_term_cursor = 1
                        while sentence_tag.get('target_word_%d' % aspect_term_cursor, ''):
                            target_word = sentence_tag.get('target_word_%d' % aspect_term_cursor)
                            target_begin = int(sentence_tag.get('target_begin_%d' % aspect_term_cursor))
                            target_end = int(sentence_tag.get('target_end_%d' % aspect_term_cursor)) + 1
                            target_polarity = sentence_tag.get('target_polarity_%d' % aspect_term_cursor)
                            aspect_term = AspectTerm(target_word, target_polarity, target_begin, target_end)
                            aspect_terms.append(aspect_term)
                            aspect_term_cursor += 1
                    sentence = AbsaSentence(sentence_text, sentence_polarity, None, aspect_terms, sentence_id,
                                            start_index_in_doc=sentence_start_index)
                    sentence_start_index += len(sentence_text)
                    sentences.append(sentence)
                weibo_text = ''.join([sentence.text for sentence in sentences])
                # for aspect_term in aspect_terms:
                #     temp = weibo_text[aspect_term.from_index: aspect_term.to_index]
                weibo = AbsaDocument(weibo_text, None, None, None, sentences, weibo_id)
                samples.append(weibo)
        samples_train, samples_dev = train_test_split(samples, test_size=0.2, random_state=self.configuration['seed'])

        samples_test = []
        test_data_dir = os.path.join(base_data_dir, 'NLP-CC2012-微博情感分析评测数据', '微博情感分析评测',
                                     'sonar-weibo-processed')
        test_filenames = os.listdir(test_data_dir)
        for test_filename in test_filenames:
            if test_filename.endswith('ann'):
                continue
            test_filepath = os.path.join(test_data_dir, test_filename)
            test_filepath_ann = re.sub('txt', 'ann', test_filepath)
            test_lines_temp = file_utils.read_all_lines(test_filepath)[1:]
            test_line_end_index = len(test_lines_temp)
            for i, line in enumerate(test_lines_temp):
                if 'root_text_begin' in line:
                    test_line_end_index = i
                    break
            test_lines = test_lines_temp[: test_line_end_index]
            test_ann_lines = file_utils.read_all_lines(test_filepath_ann)
            opinion_snippets = [line.split('\t')[2] for line in test_ann_lines if len(line) != 0]
            sentences = []
            for test_line in test_lines:
                polarity = None
                for opinion_snippet in opinion_snippets:
                    if opinion_snippet in test_line:
                        polarity = 'other'
                        break
                sentence = AbsaSentence(test_line, polarity, None, None)
                sentences.append(sentence)
            weibo_text = ''.join([sentence.text for sentence in sentences])
            # for aspect_term in aspect_terms:
            #     temp = weibo_text[aspect_term.from_index: aspect_term.to_index]
            weibo = AbsaDocument(weibo_text, None, None, None, sentences)
            samples_test.append(weibo)

        return samples_train, samples_dev, samples_test


class Semeval2014Task4(BaseDataset):
    """

    """

    def _load_semeval_by_filepath(self, train_filepath, test_filepath, val_filepath=None):
        """

        :return:
        """
        data_type_and_datas = {}
        data_type_and_filepath = {
            'train': train_filepath,
            'test': test_filepath,
            'dev': val_filepath
        }
        for data_type, filepath in data_type_and_filepath.items():
            if filepath is None:
                data_type_and_datas[data_type] = None
                continue
            content = file_utils.read_all_content(filepath)
            soup = BeautifulSoup(content, "lxml")
            sentence_tags = soup.find_all('sentence')
            sentences = []
            for sentence_tag in sentence_tags:
                text = sentence_tag.text
                aspect_term_tags = sentence_tag.find_all('aspectterm')
                aspect_terms = []
                for aspect_term_tag in aspect_term_tags:
                    term = aspect_term_tag['term']
                    polarity = aspect_term_tag['polarity']
                    from_index = aspect_term_tag['from']
                    to_index = aspect_term_tag['to']
                    aspect_term = AspectTerm(term, polarity, from_index, to_index)
                    aspect_terms.append(aspect_term)
                aspect_categories = []
                aspect_category_tags = sentence_tag.find_all('aspectcategory')
                for aspect_category_tag in aspect_category_tags:
                    category = aspect_category_tag['category']
                    polarity = aspect_category_tag['polarity']
                    aspect_category = AspectCategory(category, polarity)
                    aspect_categories.append(aspect_category)
                sentence = AbsaSentence(text, None, aspect_categories, aspect_terms)
                sentences.append(sentence)
            documents = [AbsaDocument(sentence.text, None, None, None, [sentence]) for sentence in sentences]
            data_type_and_datas[data_type] = documents
        train_data = data_type_and_datas['train']
        dev_data = data_type_and_datas['dev']
        test_data = data_type_and_datas['test']
        return train_data, dev_data, test_data


class Semeval2014Task4Lapt(Semeval2014Task4):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'SemEval-2014-Task-4-LAPT', 'origin',
                                      "SemEval'14-ABSA-TrainData_v2 & AnnotationGuidelines",
                                      'Laptop_Train_v2.xml')
        test_filepath = os.path.join(base_data_dir, 'SemEval-2014-Task-4-LAPT', 'origin',
                                     "ABSA_Gold_TestData",
                                     'Laptops_Test_Gold.xml')
        return super()._load_semeval_by_filepath(train_filepath, test_filepath)


class Semeval2014Task4Rest(Semeval2014Task4):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'SemEval-2014-Task-4-REST', 'origin',
                                      "SemEval'14-ABSA-TrainData_v2 & AnnotationGuidelines",
                                      'Restaurants_Train_v2.xml')
        test_filepath = os.path.join(base_data_dir, 'SemEval-2014-Task-4-REST', 'origin',
                                     "ABSA_Gold_TestData",
                                     'Restaurants_Test_Gold.xml')
        return super()._load_semeval_by_filepath(train_filepath, test_filepath)

    def generate_acd_and_sc_data(self, dev_size=0.2):
        """

        :return:
        """
        result = {
            'train': None,
            'dev': None,
            'test': None
        }
        distinct_categories = set()
        distinct_polarities = set()
        data_type_and_data = self.get_data_type_and_data_dict()
        for data_type, data in data_type_and_data.items():
            if data is None:
                continue
            samples = []
            for document in data:
                for sentence in document.absa_sentences:
                    content = re.sub('[\r\n]', ' ', sentence.text)
                    label = []
                    for aspect_category in sentence.aspect_categories:
                        category = aspect_category.category
                        polarity = aspect_category.polarity
                        label.append((category, polarity))
                        distinct_categories.add(category)
                        distinct_polarities.add(polarity)
                    samples.append([content, label])
            result[data_type] = samples
        super().generate_dev_data(result, dev_size)
        distinct_categories = list(distinct_categories)
        distinct_categories.sort()
        distinct_polarities = list(distinct_polarities)
        distinct_polarities.sort()
        return result, distinct_categories, distinct_polarities


class MAMSATSA(Semeval2014Task4):
    """
    2019-emnlp-A_Challenge_Dataset_and_Effective_Models_for_Aspect_Based_Sentiment_Analysis
    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'MAMS-for-ABSA', 'MAMS-ATSA', 'raw',
                                      "train.xml")
        test_filepath = os.path.join(base_data_dir, 'MAMS-for-ABSA', 'MAMS-ATSA', 'raw',
                                     "test.xml")
        val_filepath = os.path.join(base_data_dir, 'MAMS-for-ABSA', 'MAMS-ATSA', 'raw',
                                     "val.xml")
        return super()._load_semeval_by_filepath(train_filepath, test_filepath, val_filepath)


class MAMSACSA(Semeval2014Task4):
    """
    2019-emnlp-A_Challenge_Dataset_and_Effective_Models_for_Aspect_Based_Sentiment_Analysis
    """

    sentiment_path = os.path.join(base_data_dir, 'MAMS-for-ABSA', 'sentiment_dict.json')

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'MAMS-for-ABSA', 'MAMS-ACSA', 'raw',
                                      "train.xml")
        test_filepath = os.path.join(base_data_dir, 'MAMS-for-ABSA', 'MAMS-ACSA', 'raw',
                                     "test.xml")
        val_filepath = os.path.join(base_data_dir, 'MAMS-for-ABSA', 'MAMS-ACSA', 'raw',
                                     "val.xml")
        return super()._load_semeval_by_filepath(train_filepath, test_filepath, val_filepath)

    def generate_acd_and_sc_data(self, dev_size=0.2):
        """

        :return:
        """
        result = {
            'train': None,
            'dev': None,
            'test': None
        }
        distinct_categories = set()
        distinct_polarities = set()
        data_type_and_data = self.get_data_type_and_data_dict()
        for data_type, data in data_type_and_data.items():
            if data is None:
                continue
            samples = []
            for document in data:
                for sentence in document.absa_sentences:
                    content = re.sub('[\r\n]', ' ', sentence.text)
                    label = []
                    for aspect_category in sentence.aspect_categories:
                        category = aspect_category.category
                        polarity = aspect_category.polarity
                        label.append((category, polarity))
                        distinct_categories.add(category)
                        distinct_polarities.add(polarity)
                    samples.append([content, label])
            result[data_type] = samples
        super().generate_dev_data(result, dev_size)

        distinct_categories = list(distinct_categories)
        distinct_categories.sort()
        distinct_polarities = list(distinct_polarities)
        distinct_polarities.sort()
        return result, distinct_categories, distinct_polarities


class Semeval2015Task12(BaseDataset):
    """

    """

    def _load_data_by_filepath(self, train_filepath, test_filepath):
        """

        :param train_filepath:
        :param test_filepath:
        :return:
        """
        datas = []
        for filepath in [train_filepath, test_filepath]:
            if filepath is None:
                datas.append(None)
                continue
            content = file_utils.read_all_content(filepath)
            soup = BeautifulSoup(content, "lxml")
            doc_tags = soup.find_all('review')
            docs = []
            for doc_tag in doc_tags:
                sentence_tags = doc_tag.find_all('sentence')
                doc_texts = []
                sentences = []
                for sentence_tag in sentence_tags:
                    text = sentence_tag.text
                    opinion_tags = sentence_tag.find_all('opinion')
                    aspect_terms = []
                    aspect_categories = []
                    for opinion_tag in opinion_tags:
                        category = opinion_tag['category']
                        polarity = opinion_tag['polarity']
                        if 'target' in opinion_tag.attrs:
                            term = opinion_tag['target']
                            from_index = opinion_tag['from']
                            to_index = opinion_tag['to']
                            aspect_term = AspectTerm(term, polarity, from_index, to_index, category)
                            aspect_terms.append(aspect_term)
                        else:
                            aspect_category = AspectCategory(category, polarity)
                            aspect_categories.append(aspect_category)
                    sentence = AbsaSentence(text, None, aspect_categories, aspect_terms)
                    sentences.append(sentence)
                    doc_texts.append(sentence.text)
                doc = AbsaDocument(''.join(doc_texts), None, None, None, sentences)
                docs.append(doc)
            datas.append(docs)
        train_data = datas[0]
        test_data = datas[1]
        dev_data = None
        return train_data, dev_data, test_data

    def generate_acd_and_sc_data(self, dev_size=0.2):
        """

        :return:
        """
        result = {
            'train': None,
            'dev': None,
            'test': None
        }
        distinct_categories = set()
        distinct_polarities = set()
        data_type_and_data = self.get_data_type_and_data_dict()
        for data_type, data in data_type_and_data.items():
            if data is None:
                continue
            samples = []
            for document in data:
                for sentence in document.absa_sentences:
                    content = re.sub('[\r\n]+', ' ', sentence.text)
                    label = []
                    # 出现同一个entity#aspect下多个aspect term的情况不一致的情况：
                    # (1)只有中性和正向，最终为正向
                    # (2) 只有中性和负向，最终为负向
                    # (3) 既有正向也有负向，最终为conflict
                    aspect_categories_temp = {}
                    for aspect_term in sentence.aspect_terms:
                        category = aspect_term.category
                        polarity = aspect_term.polarity
                        if category not in aspect_categories_temp:
                            aspect_categories_temp[category] = set()
                        aspect_categories_temp[category].add(polarity)
                    for category, polarities in aspect_categories_temp.items():
                        if len(polarities) == 1:
                            label.append((category, polarities.pop()))
                            distinct_categories.add(category)
                            distinct_polarities.add(polarity)
                        else:
                            if ('positive' in polarities and 'negative' in polarities) or 'conflict' in polarities:
                                label.append((category, 'conflict'))
                                distinct_categories.add(category)
                                distinct_polarities.add('conflict')
                            elif 'positive' in polarities and 'neutral' in polarities:
                                label.append((category, 'positive'))
                                distinct_categories.add(category)
                                distinct_polarities.add('positive')
                            else:
                                label.append((category, 'negative'))
                                distinct_categories.add(category)
                                distinct_polarities.add('negative')
                    if len(label) == 0:
                        continue
                    samples.append([content, label])
            result[data_type] = samples
        super().generate_dev_data(result, dev_size)
        distinct_categories = list(distinct_categories)
        distinct_categories.sort()
        distinct_polarities = list(distinct_polarities)
        distinct_polarities.sort()
        return result, distinct_categories, distinct_polarities


class Semeval2016Task5Sub1(Semeval2015Task12):
    """
    Semeval2016Task5Sub1
    """

    def generate_aspect_category_detection_data(self, test_size=0.2):
        """

        :return:
        """
        result = {
            'train': None,
            'dev': None,
            'test': None
        }
        distinct_categories = set()
        for data_type, data in self.get_data_type_and_data_dict().items():
            if data is None:
                continue
            samples = []
            for document in data:
                for sentence in document.absa_sentences:
                    content = re.sub('[\r\n]', ' ', sentence.text)
                    label = []
                    for aspect_category in sentence.aspect_categories:
                        category = aspect_category.category
                        label.append(category)
                        distinct_categories.add(category)
                    samples.append([content, label])
            result[data_type] = samples
        if result['dev'] is None:
            original_train_samples = result['train']
            train_samples, dev_samples = train_test_split(original_train_samples, test_size=test_size)
            result['train'] = train_samples
            result['dev'] = dev_samples
        distinct_categories = list(distinct_categories)
        distinct_categories.sort()
        return result, distinct_categories


class Semeval2016Task5Sub2(BaseDataset):
    """

    """

    def _load_data_by_filepath(self, train_filepath, test_filepath):
        """

        :param train_filepath:
        :param test_filepath:
        :return:
        """
        datas = []
        for filepath in [train_filepath, test_filepath]:
            if filepath is None:
                datas.append(None)
                continue
            content = file_utils.read_all_content(filepath)
            soup = BeautifulSoup(content, "lxml")
            doc_tags = soup.find_all('review')
            docs = []
            for doc_tag in doc_tags:
                sentence_tags = doc_tag.find_all('sentence')
                doc_texts = []
                sentences = []
                for sentence_tag in sentence_tags:
                    text = sentence_tag.text
                    sentence = AbsaSentence(text, None, None, None)
                    sentences.append(sentence)
                    doc_texts.append(sentence.text)

                opinion_tags = doc_tag.find_all('opinion')
                aspect_terms = []
                aspect_categories = []
                for opinion_tag in opinion_tags:
                    category = opinion_tag['category']
                    polarity = opinion_tag['polarity']
                    if 'target' in opinion_tag:
                        term = opinion_tag['target']
                        from_index = opinion_tag['from']
                        to_index = opinion_tag['to']
                        aspect_term = AspectTerm(term, polarity, from_index, to_index, category)
                        aspect_terms.append(aspect_term)
                    else:
                        aspect_category = AspectCategory(category, polarity)
                        aspect_categories.append(aspect_category)
                doc = AbsaDocument(''.join(doc_texts), None, aspect_categories, aspect_terms, sentences)
                docs.append(doc)
            datas.append(docs)
        train_data = datas[0]
        test_data = datas[1]
        dev_data = None
        return train_data, dev_data, test_data

    def generate_acd_and_sc_data(self, dev_size=0.2, random_state=1234):
        """

        :return:
        """
        result = {
            'train': None,
            'dev': None,
            'test': None
        }
        distinct_categories = set()
        distinct_polarities = set()
        data_type_and_data = self.get_data_type_and_data_dict()
        for data_type, data in data_type_and_data.items():
            if data is None:
                continue
            samples = []
            for document in data:
                content = re.sub('[\r\n]', ' ', document.text)
                label = []
                for aspect_category in document.aspect_categories:
                    category = aspect_category.category
                    polarity = aspect_category.polarity
                    label.append((category, polarity))
                    distinct_categories.add(category)
                    distinct_polarities.add(polarity)
                samples.append([content, label])
            result[data_type] = samples
        super().generate_dev_data(result, dev_size, random_state=random_state)
        for data_type, data in result.items():
            category_distribution = {}
            for sample in data:
                sample_labels = [e[0] for e in sample[1]]
                for sample_label in sample_labels:
                    if sample_label not in category_distribution:
                        category_distribution[sample_label] = 0
                    category_distribution[sample_label] += 1
            category_distribution = list(category_distribution.items())
            category_distribution.sort(key=lambda x: x[0])
            logger.info('%s: %s' % (data_type, str(category_distribution)))
        distinct_categories = list(distinct_categories)
        distinct_categories.sort()
        distinct_polarities = list(distinct_polarities)
        distinct_polarities.sort()
        return result, distinct_categories, distinct_polarities

    def generate_aspect_category_detection_data(self, test_size=0.2):
        """

        :return:
        """
        result = {
            'train': None,
            'dev': None,
            'test': None
        }
        distinct_categories = set()
        for data_type, data in self.get_data_type_and_data_dict().items():
            if data is None:
                continue
            samples = []
            for document in data:
                content = re.sub('[\r\n]', ' ', document.text)
                label = []
                for aspect_category in document.aspect_categories:
                    category = aspect_category.category
                    label.append(category)
                    distinct_categories.add(category)
                samples.append([content, label])
            result[data_type] = samples
        if result['dev'] is None:
            original_train_samples = result['train']
            train_samples, dev_samples = train_test_split(original_train_samples, test_size=test_size)
            result['train'] = train_samples
            result['dev'] = dev_samples
        distinct_categories = list(distinct_categories)
        distinct_categories.sort()
        return result, distinct_categories


class Semeval2015Task12Rest(Semeval2015Task12):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'SemEval-2015-Task-12-REST', 'origin',
                                      "ABSA15_RestaurantsTrain",
                                      'ABSA-15_Restaurants_Train_Final.xml')
        test_filepath = os.path.join(base_data_dir, 'SemEval-2015-Task-12-REST', 'origin',
                                     'ABSA15_Restaurants_Test.xml')
        return super()._load_data_by_filepath(train_filepath, test_filepath)


class Semeval2015Task12Lapt(Semeval2015Task12):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'SemEval-2015-Task-12-LAPT', 'origin',
                                      "ABSA15_LaptopsTrain",
                                      'ABSA-15_Laptops_Train_Data.xml')
        test_filepath = os.path.join(base_data_dir, 'SemEval-2015-Task-12-LAPT', 'origin',
                                     'ABSA15_Laptops_Test.xml')
        return super()._load_data_by_filepath(train_filepath, test_filepath)


class Semeval2015Task12Hotel(Semeval2015Task12):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        test_filepath = os.path.join(base_data_dir, 'SemEval-2015-Task-12-HOTEL', 'origin',
                                     'ABSA15_Hotels_Test.xml')
        return super()._load_data_by_filepath(None, test_filepath)


class Semeval2016Task5ChCameSub1(Semeval2016Task5Sub1):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'SemEval-2016-Task-5-CH-CAME-SB1', 'origin',
                                      "camera_corpus",
                                      'camera_training.xml')
        test_filepath = os.path.join(base_data_dir, 'SemEval-2016-Task-5-CH-CAME-SB1', 'origin',
                                     'CH_CAME_SB1_TEST_.xml')
        return super()._load_data_by_filepath(train_filepath, test_filepath)

    def generate_acd_and_sc_data(self, dev_size=0.2):
        """

        :return:
        """
        result = {
            'train': None,
            'dev': None,
            'test': None
        }
        distinct_categories = set()
        distinct_polarities = set()
        data_type_and_data = self.get_data_type_and_data_dict()
        for data_type, data in data_type_and_data.items():
            if data is None:
                continue
            samples = []
            for document in data:
                for sentence in document.absa_sentences:
                    content = re.sub('[\r\n]+', ' ', sentence.text)
                    label = []
                    for aspect_category in sentence.aspect_categories:
                        category = aspect_category.category
                        polarity = aspect_category.polarity
                        label.append((category, polarity))
                        distinct_categories.add(category)
                        distinct_polarities.add(polarity)
                    if len(label) == 0:
                        continue
                    samples.append([content, label])
            result[data_type] = samples
        super().generate_dev_data(result, dev_size)
        distinct_categories = list(distinct_categories)
        distinct_categories.sort()
        distinct_polarities = list(distinct_polarities)
        distinct_polarities.sort()
        return result, distinct_categories, distinct_polarities


class Semeval2016Task5ChPhnsSub1(Semeval2016Task5Sub1):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'SemEval-2016-Task-5-CH-PHNS-SB1', 'origin',
                                      'Chinese_phones_training.xml')
        test_filepath = os.path.join(base_data_dir, 'SemEval-2016-Task-5-CH-PHNS-SB1', 'origin',
                                     'CH_PHNS_SB1_TEST_.xml')
        return super()._load_data_by_filepath(train_filepath, test_filepath)

    def generate_acd_and_sc_data(self, dev_size=0.2):
        """

        :return:
        """
        result = {
            'train': None,
            'dev': None,
            'test': None
        }
        distinct_categories = set()
        distinct_polarities = set()
        data_type_and_data = self.get_data_type_and_data_dict()
        for data_type, data in data_type_and_data.items():
            if data is None:
                continue
            samples = []
            for document in data:
                for sentence in document.absa_sentences:
                    content = re.sub('[\r\n]+', ' ', sentence.text)
                    label = []
                    for aspect_category in sentence.aspect_categories:
                        category = aspect_category.category
                        polarity = aspect_category.polarity
                        label.append((category, polarity))
                        distinct_categories.add(category)
                        distinct_polarities.add(polarity)
                    if len(label) == 0:
                        continue
                    samples.append([content, label])
            result[data_type] = samples
        super().generate_dev_data(result, dev_size)
        distinct_categories = list(distinct_categories)
        distinct_categories.sort()
        distinct_polarities = list(distinct_polarities)
        distinct_polarities.sort()
        return result, distinct_categories, distinct_polarities


class Semeval2016Task5LaptSub1(Semeval2016Task5Sub1):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'SemEval-2016-Task-5-LAPT-SB1', 'origin',
                                      'ABSA16_Laptops_Train_SB1_v2.xml')
        test_filepath = os.path.join(base_data_dir, 'SemEval-2016-Task-5-LAPT-SB1', 'origin',
                                     'EN_LAPT_SB1_TEST_.xml.gold')
        return super()._load_data_by_filepath(train_filepath, test_filepath)

    def generate_acd_and_sc_data(self, dev_size=0.2):
        """

        :return:
        """
        result = {
            'train': None,
            'dev': None,
            'test': None
        }
        distinct_categories = set()
        distinct_polarities = set()
        data_type_and_data = self.get_data_type_and_data_dict()
        for data_type, data in data_type_and_data.items():
            if data is None:
                continue
            samples = []
            for document in data:
                for sentence in document.absa_sentences:
                    content = re.sub('[\r\n]+', ' ', sentence.text)
                    label = []
                    for aspect_category in sentence.aspect_categories:
                        category = aspect_category.category
                        polarity = aspect_category.polarity
                        label.append((category, polarity))
                        distinct_categories.add(category)
                        distinct_polarities.add(polarity)
                    if len(label) == 0:
                        continue
                    samples.append([content, label])
            result[data_type] = samples
        super().generate_dev_data(result, dev_size)
        distinct_categories = list(distinct_categories)
        distinct_categories.sort()
        distinct_polarities = list(distinct_polarities)
        distinct_polarities.sort()
        return result, distinct_categories, distinct_polarities


class Semeval2016Task5LaptSub2(Semeval2016Task5Sub2):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'SemEval-2016-Task-5-LAPT-SB2', 'origin',
                                      'ABSA16_Laptops_Train_English_SB2.xml')
        test_filepath = os.path.join(base_data_dir, 'SemEval-2016-Task-5-LAPT-SB2', 'origin',
                                     'EN_LAPT_SB2_TEST.xml.gold')
        return super()._load_data_by_filepath(train_filepath, test_filepath)


class Semeval2016Task5RestSub1(Semeval2016Task5Sub1):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'SemEval-2016-Task-5-REST-SB1', 'origin',
                                      'ABSA16_Restaurants_Train_SB1_v2.xml')
        test_filepath = os.path.join(base_data_dir, 'SemEval-2016-Task-5-REST-SB1', 'origin',
                                     'EN_REST_SB1_TEST.xml.gold')
        return super()._load_data_by_filepath(train_filepath, test_filepath)

    def generate_aspect_category_detection_data(self, test_size=0.2):
        """

        :return:
        """
        result = {
            'train': None,
            'dev': None,
            'test': None
        }
        distinct_categories = set()
        for data_type, data in self.get_data_type_and_data_dict().items():
            if data is None:
                continue
            samples = []
            for document in data:
                for sentence in document.absa_sentences:
                    content = re.sub('[\r\n]', ' ', sentence.text)
                    label = set()
                    for aspect_term in sentence.aspect_terms:
                        category = aspect_term.category
                        label.add(category)
                        distinct_categories.add(category)
                    samples.append([content, list(label)])
            result[data_type] = samples
        if result['dev'] is None:
            original_train_samples = result['train']
            train_samples, dev_samples = train_test_split(original_train_samples, test_size=test_size)
            result['train'] = train_samples
            result['dev'] = dev_samples
        distinct_categories = list(distinct_categories)
        distinct_categories.sort()
        return result, distinct_categories

    def generate_entity_detection_data(self, test_size=0.2):
        """

        :return:
        """
        result = {
            'train': None,
            'dev': None,
            'test': None
        }
        distinct_categories = set()
        for data_type, data in self.get_data_type_and_data_dict().items():
            if data is None:
                continue
            samples = []
            for document in data:
                for sentence in document.absa_sentences:
                    content = re.sub('[\r\n]', ' ', sentence.text)
                    label = set()
                    for aspect_term in sentence.aspect_terms:
                        category = aspect_term.category.split('#')[0]
                        label.add(category)
                        distinct_categories.add(category)
                    samples.append([content, list(label)])
            result[data_type] = samples
        if result['dev'] is None:
            original_train_samples = result['train']
            train_samples, dev_samples = train_test_split(original_train_samples, test_size=test_size)
            result['train'] = train_samples
            result['dev'] = dev_samples
        distinct_categories = list(distinct_categories)
        distinct_categories.sort()
        return result, distinct_categories


class Semeval2016Task5RestSub2(Semeval2016Task5Sub2):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'SemEval-2016-Task-5-REST-SB2', 'origin',
                                      'ABSA16_Restaurants_Train_English_SB2.xml')
        test_filepath = os.path.join(base_data_dir, 'SemEval-2016-Task-5-REST-SB2', 'origin',
                                     'EN_REST_SB2_TEST.xml.gold')
        return super()._load_data_by_filepath(train_filepath, test_filepath)


def load_csv_data(filepath, skip_first_line=True):
    """

    :param filepath:
    :param skip_first_line:
    :return:
    """
    result = []
    lines = file_utils.read_all_lines(filepath)
    for line in lines:
        rows = csv.reader([line])
        for row in rows:
            result.append(row)
            if len(row) != len(result[0]):
                print(row)
    if skip_first_line:
        result = result[1:]
    return result


class Bdci2019InternetNews(BaseDataset):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        train_filepath = os.path.join(base_data_dir, 'bdci2019', '互联网新闻情感分析',
                                      'Train_DataSet.csv')
        train_label_filepath = os.path.join(base_data_dir, 'bdci2019', '互联网新闻情感分析',
                                      'Train_DataSet_Label.csv')
        train_rows = load_csv_data(train_filepath)
        train_label_rows = load_csv_data(train_label_filepath)

        test_filepath = os.path.join(base_data_dir, 'bdci2019', '互联网新闻情感分析',
                                      'Test_DataSet.csv')
        test_label_filepath = os.path.join(base_data_dir, 'bdci2019', '互联网新闻情感分析',
                                      'submit_example.csv')
        test_rows = load_csv_data(test_filepath)
        test_label_rows = load_csv_data(test_label_filepath)

        data = {
            'train': [train_rows, train_label_rows],
            'test': [test_rows, test_label_rows]
        }
        result = {}
        for data_type, [data_rows, label_rows] in data.items():
            samples = []
            for i in range(len(data_rows)):
                sample_id = data_rows[i][0]
                data = '。'.join(data_rows[i][1:])
                label = label_rows[i][1]
                sample = Text(data, label, sample_id=sample_id)
                samples.append(sample)
            result[data_type] = samples
        train_data = result['train']
        dev_data = None
        test_data = result['test']
        return train_data, dev_data, test_data


class Bdci2019FinancialNegative(BaseDataset):
    """

    """

    def __init__(self, configuration: dict = None):
        super().__init__(configuration)

    def _load_data(self):
        """

        :return:
        """
        train_filepath = os.path.join(base_data_dir, 'bdci2019', '金融信息负面及主体判定',
                                      'Train_Data.csv')
        train_rows = load_csv_data(train_filepath)
        test_filepath = os.path.join(base_data_dir, 'bdci2019', '金融信息负面及主体判定',
                                     'Test_Data.csv')
        test_label_filepath = os.path.join(base_data_dir, 'bdci2019', '金融信息负面及主体判定',
                                           'Submit_Example.csv')
        test_rows = load_csv_data(test_filepath)
        test_label_rows = load_csv_data(test_label_filepath)
        data_rows = {
            'train': train_rows,
            'test': test_rows
        }
        data = {
            'train': None,
            'test': None
        }
        for data_type, rows in data_rows.items():
            samples = []
            for row in rows:
                sample_id = row[0]
                title = row[1]
                content = row[2]
                entities = row[3].split(';')
                text_polarity = row[4] if data_type == 'train' else 0
                key_entities = row[5].split(';') if data_type == 'train' else []
                aspect_categories = []
                for entity in entities:
                    if entity in key_entities:
                        polarity = '1'
                    else:
                        polarity = '0'
                    aspect_category = AspectCategory(entity, polarity)
                    aspect_categories.append(aspect_category)
                text = '%scontent-begin。%s' % (title, content)
                document = AbsaDocument(text, text_polarity, aspect_categories, None, None, sample_id=sample_id)
                samples.append(document)
            data[data_type] = samples
        train_data = data['train']
        dev_data = None
        test_data = data['test']
        return train_data, dev_data, test_data


suported_dataset_names_and_data_loader = {
    'SemEval-2014-Task-4-LAPT': Semeval2014Task4Lapt,
    'SemEval-2014-Task-4-REST': Semeval2014Task4Rest,
    'SemEval-2015-Task-12-LAPT': Semeval2015Task12Lapt,
    'SemEval-2015-Task-12-REST': Semeval2015Task12Rest,
    'SemEval-2015-Task-12-HOTEL': Semeval2015Task12Hotel,
    'SemEval-2016-Task-5-CH-CAME-SB1': Semeval2016Task5ChCameSub1,
    'SemEval-2016-Task-5-CH-PHNS-SB1': Semeval2016Task5ChPhnsSub1,
    'SemEval-2016-Task-5-LAPT-SB1': Semeval2016Task5LaptSub1,
    'SemEval-2016-Task-5-LAPT-SB2': Semeval2016Task5LaptSub2,
    'SemEval-2016-Task-5-REST-SB1': Semeval2016Task5RestSub1,
    'SemEval-2016-Task-5-REST-SB2': Semeval2016Task5RestSub2,
    'bdci2019-internet-news-sa': Bdci2019InternetNews,
    'bdci2019-financial-negative': Bdci2019FinancialNegative,
    'MAMSACSA': MAMSACSA,
    'MAMSATSA': MAMSATSA,
    'nlpcc2012-weibo-sa': Nlpcc2012WeiboSa,
}


def get_dataset_class_by_name(dataset_name):
    """

    :param dataset_name:
    :return:
    """
    return suported_dataset_names_and_data_loader[dataset_name]
