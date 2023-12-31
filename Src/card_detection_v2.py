import cv2
import torch
import numpy as np
from torchvision import transforms
from PIL import Image
from Utils.model_definition import ResNet34
from Utils.helper import *
import matplotlib.pyplot as plt 

MIN_WIDTH = 50  # minimum width of the contour to be considered a card
MIN_HEIGHT = 70  # minimum height of the contour to be considered a card

def make_square(image):
    width, height = image.size

    # Determine the new size for the shortest dimension
    new_size = max(width, height)

    # Create a new square image with a black background
    new_image = Image.new('RGB', (new_size, new_size), (0, 0, 0))

    # Calculate the position to paste the original image onto the new square background
    paste_x = (new_size - width) // 2
    paste_y = (new_size - height) // 2

    # Paste the original image onto the new square background
    new_image.paste(image, (paste_x, paste_y))

    return new_image

card_mapping = create_card_mapping()

# Load your trained ResNet34 model
model = torch.load('Models\TrainedModels\jass_card_classifier_model_v4.pth',map_location=torch.device('cpu'))
model.eval()

# Define the transformation needed for the ResNet34 input
transform = transforms.Compose([
    transforms.Resize((224, 224)),  # Resize directly to 224x224, maintaining aspect ratio
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Initialize video capture
cap = cv2.VideoCapture(1)

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()
    if not ret:
        break

    # Convert to grayscale just for thresholding and contour detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    """
    # Plot using Matplotlib
    plt.imshow(gray, cmap='gray')
    plt.title("Grayscale Image")
    plt.show()

    # Plot using Matplotlib
    plt.imshow(thresh, cmap='gray')
    plt.title("Grayscale Image Contrast")
    plt.show()
    """

    # Process each contour
    for contour in contours:
        # Approximate contour to polygon
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

        # Check if the contour has 4 vertices (potential card)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)

            # Process the contour only if it meets the size thresholds
            if w >= MIN_WIDTH and h >= MIN_HEIGHT:
                # Extract the ROI using the original RGB frame
                roi = frame[y:y+h, x:x+w]
                # Ensure that the ROI is converted to RGB if your camera captures in BGR
                roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                roi_pil = Image.fromarray(roi)
                roi_pil = make_square(roi_pil)
                roi_tensor = transform(roi_pil).unsqueeze(0)

                
                # # Unnormalize the tensor
                # mean = np.array([0.485, 0.456, 0.406])
                # std = np.array([0.229, 0.224, 0.225])
                # roi_unnorm = torch.squeeze(roi_tensor)  # Remove batch dimension
                # roi_unnorm = roi_unnorm * torch.tensor(std[:, None, None]) + torch.tensor(mean[:, None, None])
                # roi_unnorm = roi_unnorm.numpy()

                # # Transpose from (C, H, W) to (H, W, C)
                # roi_unnorm = np.transpose(roi_unnorm, (1, 2, 0))

                # # Plot using Matplotlib
                # plt.imshow(roi_unnorm)
                # plt.title("ROI Tensor Visualized")
                # plt.show()
                
                # Make a prediction
                with torch.no_grad():
                    prediction = model(roi_tensor)
                max_index = torch.argmax(prediction).item()

                # Get the corresponding card label
                card_label = card_mapping[max_index]

                # Draw bounding box and label on the frame
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, str(card_label), (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    # Display the resulting frame
    cv2.imshow('Card Detection', frame)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the capture
cap.release()
cv2.destroyAllWindows()