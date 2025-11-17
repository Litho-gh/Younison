# Code adapted from GeeksforGeeks media player example
from tkinter import filedialog

import requests
from tkinter import *
from tkinter import messagebox
import pygame
import os

# Download the image from the web
def download_image(image_url,file_name):
    response = requests.get(image_url)
    with open(file_name, 'wb') as file:
        file.write(response.content)

download_image('https://media.geeksforgeeks.org/wp-content/uploads/20240610151925/background.png','background.png')
download_image('https://media.geeksforgeeks.org/wp-content/uploads/20240610151926/next.png','next.png')
download_image('https://media.geeksforgeeks.org/wp-content/uploads/20240610151926/pause.png','pause.png')
download_image('https://media.geeksforgeeks.org/wp-content/uploads/20240610151926/play.png','play.png')
download_image('https://media.geeksforgeeks.org/wp-content/uploads/20240610151926/previous.png','previous.png')



# Initialize the Tkinter window
app = Tk()
app.title('Younison')
app.geometry("900x700")

# Change the application icon
app_icon = PhotoImage(file='background.png')
app.iconphoto(False, app_icon)

# Initialize Pygame's mixer module for playing audio
pygame.mixer.init()

# Define an event for when a song ends
SONG_END_EVENT = pygame.USEREVENT + 1
pygame.mixer.music.set_endevent(SONG_END_EVENT)

# Create a menu bar
menu_bar = Menu(app)
app.config(menu=menu_bar)

# Define global variables
playlist = []  # List to store names of songs
current_song = ""  # Store the currently playing song
is_paused = False  # Flag to indicate if music is paused
global_artist = "null"

# Artist Info Click Function
def click():
    separator = '-'
    result = global_artist.split(separator, 1)[0] # truncate current song name to retrieve artist name
    if global_artist == "null":
        messagebox.showinfo(title='Artist Summary', message='No Artist Detected')
    else:
        wiki_artist_info = get_artist_info(result)
        messagebox.showinfo(title='Artist Info', message=wiki_artist_info)

my_button = Button(app, command=click,text='Show Artist Info')

if global_artist == "null":
    my_button.pack()

#################### API HANDLING ####################
def get_artist_info(artist):

    #API request
    global global_artist # modifying global variable artist
    # Summary Endpoint: used for artist summaries
    url = "https://wikipedia-api2.p.rapidapi.com/summary"

    artist = artist

    querystring = {"title":artist}

    headers = {
	    "x-rapidapi-key": "823c5e01cdmsha56154e40f41b55p1c80c3jsn68d73c8894ae",
	    "x-rapidapi-host": "wikipedia-api2.p.rapidapi.com"
    }

    wiki_response = requests.get(url, headers=headers, params=querystring)

    # Print result from API
    api_response = wiki_response.json()
    # global_artist = api_response['summary']
    api_return = api_response['summary']
    return api_return
# print(wiki_print['summary'])

# my_label = Label(app,text=get_artist_info("King Gizzard and the Lizard Wizard"))
# my_label.place(x=0,y=300)







# Function to load music from a directory
def load_music():
    global current_song
    global global_artist
    app.directory = filedialog.askdirectory()

    # Clear the current list of songs
    playlist.clear()
    song_listbox.delete(0, END)

    # Iterate through files in the directory and add MP3 files to the playlist
    for file in os.listdir(app.directory):
        name, ext = os.path.splitext(file)
        if ext == '.mp3':
            playlist.append(file)

    # Add songs to the listbox
    for song in playlist:
        song_listbox.insert("end", song)

    # Select the first song in the list by default, if there are any songs
    if playlist:
        song_listbox.selection_set(0)
        current_song = playlist[song_listbox.curselection()[0]]



# Function to play music
def play_music(event=None):
    global current_song, is_paused, global_artist

    print(current_song)
    global_artist = current_song

    if not playlist:
        return

    # Get the selected song from the listbox
    current_selection = song_listbox.curselection()
    if current_selection:
        current_song = playlist[current_selection[0]]

    # If not paused, load and play the current song
    if not is_paused:
        pygame.mixer.music.load(os.path.join(app.directory, current_song))
        pygame.mixer.music.play()
    else:
        # If paused, unpause the music
        pygame.mixer.music.unpause()
        is_paused = False

# Function to pause music
def pause_music():
    global is_paused
    if not playlist:
        return
    pygame.mixer.music.pause()
    is_paused = True

# Function to play the next song
def next_song():
    global current_song, is_paused

    if not playlist:
        return

    try:
        # Clear previous selection and select the next song in the list
        song_listbox.selection_clear(0, END)
        next_index = (playlist.index(current_song) + 1) % len(playlist)
        song_listbox.selection_set(next_index)
        current_song = playlist[song_listbox.curselection()[0]]
        is_paused = False  # Reset paused flag for next song
        play_music()
    except:
        pass

# Function to play the previous song
def previous_song():
    global current_song, is_paused

    if not playlist:
        return

    try:
        # Clear previous selection and select the previous song in the list
        song_listbox.selection_clear(0, END)
        prev_index = (playlist.index(current_song) - 1) % len(playlist)
        song_listbox.selection_set(prev_index)
        current_song = playlist[song_listbox.curselection()[0]]
        is_paused = False  # Reset paused flag for previous song
        play_music()
    except:
        pass

# Function to check if the music has ended
def check_music_end():
    if not pygame.mixer.music.get_busy() and not is_paused and playlist:
        next_song()
    app.after(100, check_music_end)

# Create a menu for adding songs
add_songs_menu = Menu(menu_bar, tearoff=False)
add_songs_menu.add_command(label='Select Folder', command=load_music)
menu_bar.add_cascade(label='Add Songs', menu=add_songs_menu)

# Create a listbox to display songs
song_listbox = Listbox(app, bg="green", fg="white", width=100, height=13)
song_listbox.pack()

# Bind a selection event to the listbox
song_listbox.bind("<<ListboxSelect>>", play_music)

# Load images for control buttons
play_button_image = PhotoImage(file='play.png')
pause_button_image = PhotoImage(file='pause.png')
next_button_image = PhotoImage(file='next.png')
previous_button_image = PhotoImage(file='previous.png')

# Create control buttons
control_frame = Frame(app)
control_frame.pack()

play_button = Button(control_frame, image=play_button_image, borderwidth=0, command=play_music)
pause_button = Button(control_frame, image=pause_button_image, borderwidth=0, command=pause_music)
next_button = Button(control_frame, image=next_button_image, borderwidth=0, command=next_song)
previous_button = Button(control_frame, image=previous_button_image, borderwidth=0, command=previous_song)

# Arrange control buttons
previous_button.grid(row=0, column=0, padx=5)
play_button.grid(row=0, column=1, padx=5)
pause_button.grid(row=0, column=2, padx=5)
next_button.grid(row=0, column=3, padx=5)

# Start checking for the end of song event
app.after(100, check_music_end)

# Start Tkinter event loop
app.mainloop()

#This code is contributed by sourabh_jain

