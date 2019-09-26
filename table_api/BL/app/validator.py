# -*- coding: utf-8 -*-
"""
Created on Sun Jun 17 11:20:54 2018

@author: Amith-Algonox
"""
import re
import json
# import db
try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()

def get_parameters():
    with open('./parameters.json') as f:
        return json.loads(f.read())

host_ = "127.0.0.1"
user_ = "root"
password_ = ""

parameters = get_parameters()

ANALYST_DATABASE = parameters['database_name']
def execute_query(sql, db=ANALYST_DATABASE):
    data = None
    conn = pymysql.connect(host=host_, user=user_, password=password_, db=db,
        use_unicode=True, charset='utf8')
    try:
        a = conn.cursor()
        a.execute(sql)
        data = a.fetchall()
        conn.commit()
    except Exception as e:
        logging.exception(f'{e}')
        with open('sql.txt', 'w') as f:
            f.write(sql)
        conn.rollback()
    conn.close()
    return data


class Regex(object):
    def __init__(self):
        self.rules_dict = {'a': '[a-zA-Z]',
                           'n': '\d',
                           's': '\W',
                           'an': '[a-zA-Z0-9]'}
        self.regex_path = 'configs/regex.json'

    def validate(self, string, pattern):
        '''
        Validate string against the regex of the field specified.

        :param string: (str) String that regex should be applied to. (Required)
        :param field: (str) What field the string is supposed to be. (Required)
        :returns: (str) Result if matched, else not-found message.
        '''

        if pattern == '':
            #print('NO REGEX DETECTED', field)
            return string

        if string:
            result = re.findall(pattern, string)
        else:
            return ''

        if result != []:
            #print('\nPattern Matched!')
            #print('Text:\t', string)
            #print('Regex:\t', pattern)
            #print('Result:\t', result[-1])
            return result[-1]
        else:
            #print('\nValidation Failed!')
            #print('Text:\t', string)
            #print('Regex:\t', pattern)
            #print('Result:\t', result)
            return 'validation failed!{}'.format(string)

    def generate(self, rules):
        '''
        Generate regex from the list of rules.

        :param rules: (list) List of what each character is supposed to be. (Required)
                      ex: "12-ab" -> ['d', 'd', 's', 'w', 'w']
        :returns: (str) The regex pattern.
        '''
        regex = []
        count = []
        prev = ''

        for idx, char in enumerate(rules):
            if char in self.rules_dict:
                if char is prev:
                    count[-1] += 1
                else:
                    regex.append(self.rules_dict[char])
                    count.append(1)

            prev = char

        pattern = ''

        for idx, char_class in enumerate(regex):
            if count[idx] > 1:
                pattern += char_class + '{' + str(count[idx]) + '}'
            else:
                pattern += char_class

        # print('\nGenerated pattern:', pattern)

        return pattern

    def save_regex(self, field, pattern):
        '''
        Save the regex pattern to the corresponding field.

        :param field: (str) Field to which the regex belongs to. (Required)
        :param pattern: (str) Corresponding regex pattern. (Required)
        '''
        with open(self.regex_path, 'r') as fp:
            config_data = json.loads(fp.read())

        config_data[field] = pattern

        with open(self.regex_path, 'w') as fp:
            fp.write(json.dumps(config_data, indent = 4))

        # print('Regex config file updated.')

    def if_pattern_exists(self, field):
        '''
        Check if pattern already exists in the regex.json

        :param field: (str) Name of the pattern. (Required)
        :returns: (bool) True if exists, else False
        '''
        with open(self.regex_path, 'r') as fp:
            config_data = json.loads(fp.read())

        return field in config_data

    def get_pattern(self, type):
        validator_query="SELECT field,pattern FROM validation_data WHERE field!='NONE'"
        validations=  execute_query(validator_query)
        regex_data={}
        if(len(validations)>0):
            for i in validations:
                regex_data[i[0]]=i[1]
        return regex_data[type] if type in regex_data else ''

#rules = ['n', 'n', 'n', 'a']
#reg = Regex()
#reg.generate(rules, 'test')
#reg.validate('234A', 'test')
