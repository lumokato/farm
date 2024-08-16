import json, os
import copy

def trans_farm():
    with open('account.json', 'r') as f:
        data = json.load(f)

    with open('auto/json/farm_example.json', 'r') as fp:
        example = json.load(fp)
    clan_count = {
        0: 0,
        3: 0,
        39: 0,
        53: 0,
        54: 0
    }
    for account in data['accounts']:
        save_data = copy.deepcopy(example)
        save_data['username'] = account['uid']
        if account['clan_id'] == 3:
            save_data['config']['underground_donate'] = 119
            save_data['config']['time_cron1'] = '08:02'
            save_data['config']['time_cron2'] = '20:02'
        if account['clan_id'] == 54:
            save_data['config']['underground_donate'] = 118
            save_data['config']['time_cron1'] = '08:04'
            save_data['config']['time_cron2'] = '20:04'
        if account['clan_id'] == 53:
            save_data['config']['time_cron1'] = '08:06'
            save_data['config']['time_cron2'] = '20:06'
        
        save_dir = 'auto/json/' + str(account['clan_id']) + '-' + str(clan_count[account['clan_id']]) + '.json'
        clan_count[account['clan_id']] += 1
        with open(save_dir, 'w') as fp:
            json.dump(save_data, fp)



    return 0

if __name__ == "__main__":
    trans_farm()