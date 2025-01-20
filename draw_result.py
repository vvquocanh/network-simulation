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

plot_response_times("data_full.csv", 10, 100)