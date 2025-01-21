import pandas as pd
import matplotlib.pyplot as plt

def plot_response_times(csv_file, min_burstiness, max_burstiness):
    data = pd.read_csv(csv_file)
    filtered_data = data[(data['burstiness'] >= min_burstiness) & (data['burstiness'] <= max_burstiness)]
    
    # Plot the response times
    plt.figure(figsize=(10, 6))
    
    plt.plot(filtered_data['burstiness'], filtered_data['data_response_time'], label='Data Response Time', marker='o')
    plt.plot(filtered_data['burstiness'], filtered_data['voice_response_time'], label='Voice Response Time', marker='o')
    plt.plot(filtered_data['burstiness'], filtered_data['video_response_time'], label='Video Response Time', marker='o')
    plt.plot(filtered_data['burstiness'], filtered_data['total_response_time'], label='Total Response Time', marker='o')
    
    # Customize the plot
    plt.title('Response Time')
    plt.xlabel('Burstiness')
    plt.ylabel('Average Response Time')
    plt.xticks(filtered_data['burstiness'])
    plt.legend()
    plt.grid(True)
    
    # Show the plot
    plt.tight_layout()
    plt.show()

def plot_sent_packet_proportion(csv_file, min_burstiness, max_burstiness):
    data = pd.read_csv(csv_file)

    filtered_data = data[(data['burstiness'] >= min_burstiness) & (data['burstiness'] <= max_burstiness)]

    # Calculate percentage contribution for each source
    filtered_data['data_percentage'] = filtered_data['data_sent_packet'] / filtered_data['total_sent_packet'] * 100
    filtered_data['voice_percentage'] = filtered_data['voice_sent_packet'] / filtered_data['total_sent_packet'] * 100
    filtered_data['video_percentage'] = filtered_data['video_sent_packet'] / filtered_data['total_sent_packet'] * 100

    # Plot the stacked bar chart
    plt.figure(figsize=(10, 6))
    
    x = filtered_data['burstiness']
    
    # Set a fixed bar width
    bar_width = (max_burstiness - min_burstiness) / (len(x) * 2) # You can adjust this value between 0 and 1
    
    # Stack the bars with fixed width
    plt.bar(x, filtered_data['data_percentage'], width=bar_width, label='Data')
    plt.bar(x, filtered_data['voice_percentage'], width=bar_width,
            bottom=filtered_data['data_percentage'], label='Voice')
    plt.bar(x, filtered_data['video_percentage'], width=bar_width,
            bottom=filtered_data['data_percentage'] + filtered_data['voice_percentage'], 
            label='Video')

    # Add labels, title, and legend
    plt.title('Proportion of Sent Packets by Source')
    plt.xlabel('Burstiness')
    plt.ylabel('Percentage of Sent Packets')
    plt.xticks(x)
    plt.legend()

    plt.tight_layout()
    plt.show()

def calculate_slope(csv_file):
    data = pd.read_csv(csv_file)
    
    data_slope = data['data_response_time'].diff() / data['burstiness'].diff()
    print(f'Data Slope: {data_slope.mean() * 1000}')
    
    voice_slope = data['voice_response_time'].diff() / data['burstiness'].diff()
    print(f'Voice Slope: {voice_slope.mean() * 1000}')
    
    video_slope = data['video_response_time'].diff() / data['burstiness'].diff()
    print(f'Video Slope: {video_slope.mean() * 1000}')
    
    total_slope = data['total_response_time'].diff() / data['burstiness'].diff()
    print(f'Total Slope: {total_slope.mean() * 1000}')
    
#plot_sent_packet_proportion("data_full.csv", 10, 100)
#plot_response_times("data_full.csv", 10, 100)

calculate_slope("data_100.csv")