rank12 = [
    '21-7',
    '21-11',
    '21-12',
    '20-9',
    '20-1',
    '20-9',
    '20-2',
    '19-5'
    '19-7',

]
rank11 = [
    '18-13',
    '17-5',
    '17-12',
    '16-2',
    '16-14'
]
rank10 = [
    '15-5',
    '14-1',
    '14-5',
    '14-8',
    '14-13'
]
rank9 = [
    '13-5',
    '13-6',
    '13-7',
    '12-14',
    '12-13',
    '12-11',
]
rank8 = [
    '11-14',
    '11-12',
    '11-7',
]
rank7 = [
    '8-2',
    '8-12',
    '8-14',
    '7-7',
    '5-11',
]
rank1 = [
    '1-1',
]


def shuatu_list(max_tu_num):
    if max_tu_num > 11022000:    # >298
        return rank12 + rank11 + rank8
    elif max_tu_num > 11017000:  # >228
        return rank11 + rank10 + rank7
    elif max_tu_num > 11012000:  # >152
        return rank10 + rank9 + rank8
    else:
        return rank7 + rank1
