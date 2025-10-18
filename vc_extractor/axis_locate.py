import cv2
import matplotlib.pyplot as plt

def show_click_coords(img, rotation, title):
    if rotation == 0:
        show_img = img
    elif rotation == 90:  # 順時針90度
        show_img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 180:
        show_img = cv2.rotate(img, cv2.ROTATE_180)
    else:
        raise ValueError("rotation must be 0, 90, 180")
    fig, ax = plt.subplots()
    ax.imshow(cv2.cvtColor(show_img, cv2.COLOR_BGR2RGB))
    ax.set_title(title)
    print(f"\n[點擊{title}圖片以取得座標，關閉視窗結束]")
    def onclick(event):
        if event.inaxes:
            x, y = int(event.xdata), int(event.ydata)
            if rotation == 0:
                orig_x, orig_y = x, y
            elif rotation == 90:
                orig_x = img.shape[0] - 1 - y
                orig_y = x
            elif rotation == 180:
                orig_x = img.shape[1] - 1 - x
                orig_y = img.shape[0] - 1 - y
            print(f"你點擊的座標 (旋轉後): ({x},{y})  對應原圖座標: ({orig_x},{orig_y})")
            ax.plot(x, y, 'ro')
            ax.annotate(f"{x},{y}\n({orig_x},{orig_y})", (x, y), color='red', fontsize=8)
            fig.canvas.draw()
    fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()

if __name__ == "__main__":
    img = cv2.imread('302132426.png')
    show_click_coords(img, rotation=0, title="原圖")
    show_click_coords(img, rotation=90, title="順時針90度")
    show_click_coords(img, rotation=180, title="旋轉180度")