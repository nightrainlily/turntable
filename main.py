import import_ipynb
from ml import closest

def recommendation(p):
    return f"Output playlist: {rec}"

if __name__ == "__main__":
    in_playlist = input("Input playlist: ")
    rec = closest(in_playlist)

    out = recommendation(in_playlist)
    print(out)