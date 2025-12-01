# Code adapted from GeeksforGeeks media player example: https://www.geeksforgeeks.org/python/build-a-music-player-with-tkinter-and-pygame-in-python/
# Implemented into Younison project by Wren Hallie and River Hallie
# v1.0 11/30/2025

from tkinter import filedialog
import requests
from tkinter import *
from tkinter import messagebox
import pygame
import os
import api_info
from google.cloud import storage
import socket
import threading, wave, pyaudio, time
from pathlib import Path
import json
import time


############################################################ Cloud Storage Handling ############################################################
# Connect to GCloud Storage API
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'final-project-479801-420b89054971.json'
storage_client = storage.Client()

# Create new bucket
def create_new_bucket(bucket_name, location):
    name = bucket_name
    new_bucket = storage_client.bucket(name)
    new_bucket = storage_client.create_bucket(new_bucket, location=location)
    return new_bucket

#bucket = create_new_bucket("new_younison_bucket", "us")

#Print bucket details
#vars(bucket)

# Accessing specific Bucket
my_bucket = storage_client.get_bucket("new_younison_bucket")

"""
Uploads to specified bucket
filepath is local path on machine to upload to cloud storage
"""
def upload_to_bucket(blob_name, file_path, bucket_name):
    try:
        loc_bucket = storage_client.get_bucket(bucket_name)
        blob = my_bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
        return True
    except Exception as e:
        print(e)
        return False

# Downloading Files from bucket
def download_file_from_bucket(blob_name, file_path, bucket_name):
    try:
        loc_bucket = storage_client.get_bucket(bucket_name)
        blob = my_bucket.blob(blob_name)
        with open(file_path, 'wb') as f:
            storage_client.download_blob_to_file(blob, f)
        return True
    except Exception as e:
        print(e)
        return False

#################################################################################################################################################

api_info = api_info

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
global_artist = "null" # Store artist name for API lookup
song_start_time = None # tracks when user begins listening
accumulated_listen_time = 0 # Global Clock for time listened in seconds


# Artist Info Click Function
def click():
    separator = '-'
    result = global_artist.split(separator, 1)[0] # truncate current song name to retrieve artist name
    if global_artist == "null":
        messagebox.showinfo(title='Artist Summary', message='No Artist Detected')
    else:
        wiki_artist_info = get_artist_info(result)
        messagebox.showinfo(title='Artist Info', message=wiki_artist_info)

artist_info_button = Button(app, command=click,text='Show Artist Info')

if global_artist == "null":
    artist_info_button.pack()

######################################## API HANDLING ########################################
api_key = api_info.api_key # api key for calls

def get_artist_info(artist):
    #API request
    global global_artist # modifying global variable artist
    # Summary Endpoint: used for artist summaries
    url = "https://wikipedia-api2.p.rapidapi.com/summary"

    artist = artist

    querystring = {"title":artist}

    headers = {
	    "x-rapidapi-key": api_key,
	    "x-rapidapi-host": "wikipedia-api2.p.rapidapi.com"
    }

    wiki_response = requests.get(url, headers=headers, params=querystring)

    # Print result from API
    api_response = wiki_response.json()
    # global_artist = api_response['summary']
    api_return = api_response['summary']
    return api_return

#################################################################################################

######################################## User Metrics ##########################################
MIN_PLAY_TIME = 30 # 30 seconds to count a play
def load_data(filename="userdata.json"):
    if not os.path.exists(filename):
        print("Downloading json from bucket...")
        cloud_json = download_file_from_bucket('userdata.json', os.path.join(os.getcwd(), 'userdata.json'), "new_younison_bucket")
        print("Successfully downloaded...")
        print(json.dumps(cloud_json))
        return cloud_json
    with open(filename, "r") as f:
        loaded_data = json.load(f)
        return loaded_data

def save_data(data, filename="userdata.json"):
    with open(filename, "w") as f: # updates local json object
        json.dump(data, f, indent=4)
    upload_to_bucket('userdata.json', os.path.join(os.getcwd(), 'userdata.json'), "new_younison_bucket")

def record_play(artist, song, data):
    data["history"].append({    # update listening history
        "artist": artist,
        "song": song,
    })

    # update song play count
    key = f"{artist} - {song}"
    data["song_play_count"][key] = data["song_play_count"].get(key, 0) + 1
    # update artist play count
    data["artist_play_count"][artist] = data["artist_play_count"].get(artist, 0) + 1

user_data_json = load_data()
print("Initial json object")
print(json.dumps(user_data_json, indent=4)) # print json for debug

def format_time(seconds):
    minutes = seconds //60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"

def save_listened_time_to_json(listened, path="userdata.json"):
    with open(path, "r") as f: # load old data
        data = json.load(f)

    data["total_time_listened"] = data.get("total_time_listened", 0) + listened # update total time listened on json

    with open(path, "w") as f:  # Save to json
        json.dump(data, f, indent=4)

def print_table_metrics(data):
    lines = ["========== Listening Metrics!! ==========\n", f"========== Song Count ==========\n"]
    for song, count in data["song_play_count"].items():
        lines.append(f"{song}: {count} plays")

    lines.append("========== Artist Play Count ==========\n")
    for artist, count in data["artist_play_count"].items():
        lines.append(f"{artist}: {count} plays")

    lines.append("========== Time Listened ==========\n")
    time_listened = data["total_time_listened"]
    lines.append(f"Total time you've listened: {format_time(time_listened)}")

    lines.append("========== Recent History =========\n")
    for entry in data["history"][-5:]:
        lines.append(f" • {entry['artist']} - {entry['song']}")
    return "\n".join(lines)

def metrics_click(filename="userdata.json"):
    if os.path.exists(filename):
        data = load_data() # loads user data from user data json object
        metrics = print_table_metrics(data)
        messagebox.showinfo(title='Listening Metrics', message=metrics)
    else:
        messagebox.showinfo(title='Listening Metrics', message="There has been an error, please try again.")

listen_metrics_button = Button(app, command=metrics_click,text='Listening Metrics')

listen_metrics_button.pack()

##################################################################################################

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
    global current_song, is_paused, global_artist, song_start_time, accumulated_listen_time, MIN_PLAY_TIME

    print(current_song) # print value of current song in terminal for debugging
    global_artist = current_song # assigning global artist
    if global_artist != "null":
        song_start_time = time.time() # start timer when music starts
        accumulated_listen_time = 0 # reset buffer for this play
        artist_data, song_data = global_artist.split('-', 1)
        song_data = os.path.splitext(song_data) [0]
        print("artist data:", artist_data)
        print("song data:", song_data)
        data = load_data() # load json object
        print(json.dumps(data, indent=4))

        record_play(artist_data, song_data, data) # add current song playing to json
        save_data(data)


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
    global is_paused, song_start_time, accumulated_listen_time
    if song_start_time is None:
        return 0
    if not playlist:
        return 0
    pygame.mixer.music.pause()
    is_paused = True
    listened = int(time.time() - song_start_time)
    accumulated_listen_time += listened
    song_start_time = 0 # reset clock
    save_listened_time_to_json(listened)
    return 0


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

############################## Capture Window Close Event ##############################
def on_close():
    filepath = "userdata.json"
    data = load_data()
    upload_to_bucket('userdata.json', os.path.join(os.getcwd(), 'userdata.json'), "new_younison_bucket")
    if os.path.exists(filepath):
        os.remove(filepath)
        print("User data has been deleted.")
    else:
        print("File does not exist.")
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_close)


# Start Tkinter event loop
app.mainloop()




