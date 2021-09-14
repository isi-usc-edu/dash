from nltk.corpus import words
from nltk.tokenize import wordpunct_tokenize
from collections import Counter


# source http://stackoverflow.com/questions/195010/how-can-i-split-multiple-joined-words/481773#481773
def viterbi_segment(text, dictionary, total, max_word_length):
    probs, lasts = [1.0], [0]
    for i in range(1, len(text) + 1):
        prob_k, k = max((probs[j] * word_prob(text[j:i], dictionary, total), j)
                        for j in range(max(0, i - max_word_length), i))
        probs.append(prob_k)
        lasts.append(k)
    words = []
    i = len(text)
    while 0 < i:
        words.append(text[lasts[i]:i])
        i = lasts[i]
    words.reverse()

    # probabilities unnecessary for now
    # return words, probs[-1]
    return words


def word_prob(word, dictionary, total):
    return dictionary[word] / total


def count(string):
    dictionary = Counter(words.words())
    max_word_length = max(list(map(len, dictionary)))
    total = float(sum(dictionary.values()))
    tokenized = wordpunct_tokenize(string)
    out = []

    total_cost = 0
    for token in tokenized:
        # for now, assume cognitive load of remembering a word is the same regardless
        # of letter case
        token = token.lower()
        words_in_token = viterbi_segment(token, dictionary, total, max_word_length)
        num_words_in_token = len(words_in_token)
        total_cost += num_words_in_token
        out.append(words_in_token)

    return (total_cost, out)

print((count("hello&^uevfehello!`.<hellohow*howdhAreyouargument")))
print((count("hellogoodbye")))
