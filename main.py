import import_ipynb
from ml import closest
import pandas as pd

def recommendation(p):
    return f"Output playlist: {rec}"

def get_playlist_link(playlist):
    playlists = pd.read_csv('csv_files/playlists.csv')
    row = playlists.iloc['name' == playlist]
    link = row['link']
    return link

if __name__ == "__main__":
    in_playlist = input("Input playlist: ")
    rec = closest(in_playlist)

    out = recommendation(in_playlist)
    print(out)