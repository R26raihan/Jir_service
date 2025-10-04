import streamlit as st
import cv2
import torch
from torchvision import transforms
from backend.preciction.model import CSRNet
from PIL import Image
import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import time
import os
import tempfile

# Setup Streamlit
st.set_page_config(layout="wide")
st.title("Crowd Counting via CCTV (CSRNet)")
st.markdown("Streaming + Prediksi Jumlah Orang dari ROI dengan CSRNet")

# Setup device & model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

@st.cache_resource
def load_model():
    model = CSRNet().to(device)
    weights_path = r"C:\CrowdCounting-using-CRSNet-main\backend\preciction\weights.pth"
    checkpoint = torch.load(weights_path, map_location=device)
    model.load_state_dict(checkpoint)
    model.eval()
    return model

model = load_model()

# ROI dan URL
cctv_urls = {
    "DPR": "https://cctv.balitower.co.id/Bendungan-Hilir-003-700014_1/embed.html",
    "Patung Kuda": "https://cctv.balitower.co.id/JPO-Merdeka-Barat-507357_9/embed.html",
}

roi_polygons = {
    "Patung Kuda": np.array([[224, 675], [392, 383], [644, 377], [970, 671]], dtype=np.int32),
    "DPR": np.array([[7, 346], [1067, 375], [1070, 513], [5, 454]], dtype=np.int32),
    "default": None
}

# Setup Selenium
chrome_driver_path = r"C:\CrowdCounting-using-CRSNet-main\chromedriver-win64\chromedriver.exe"
driver_service = Service(chrome_driver_path)

# Pilih lokasi
selected_location = st.selectbox("Pilih Lokasi CCTV", list(cctv_urls.keys()))
roi_polygon = roi_polygons.get(selected_location, roi_polygons["default"])

if st.button("Ambil dan Prediksi"):
    with st.spinner("Mengambil screenshot dan memproses..."):
        driver = None
        try:
            driver = webdriver.Chrome(service=driver_service)
            driver.get(cctv_urls[selected_location])
            time.sleep(5)

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                screenshot_path = tmpfile.name
                driver.save_screenshot(screenshot_path)

            frame = cv2.imread(screenshot_path)
            frame = cv2.resize(frame, (1080, 720))
            os.remove(screenshot_path)

            display_frame = frame.copy()

            if roi_polygon is not None:
                mask = np.zeros_like(frame[:, :, 0])
                cv2.fillPoly(mask, [roi_polygon], 255)
                roi_frame = cv2.bitwise_and(frame, frame, mask=mask)

                # Tambahkan overlay hijau transparan dan garis ROI
                overlay = display_frame.copy()
                cv2.fillPoly(overlay, [roi_polygon], color=(0, 255, 0))
                cv2.addWeighted(overlay, 0.3, display_frame, 0.7, 0, display_frame)
                cv2.polylines(display_frame, [roi_polygon], isClosed=True, color=(0, 255, 0), thickness=2)
            else:
                roi_frame = frame

            # Prediksi
            pil_img = Image.fromarray(cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB))
            img_tensor = transform(pil_img).unsqueeze(0).to(device)
            with torch.no_grad():
                output = model(img_tensor)
            count = int(output.sum().item())

            # Tambahkan hasil prediksi ke frame
            cv2.putText(display_frame, f"Prediksi: {count} orang", (30, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)

            # Konversi ke PIL
            final_img = Image.fromarray(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))
            roi_img = Image.fromarray(cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB))

            # Tampilkan di Streamlit
            col1, col2 = st.columns(2)
            with col1:
                st.image(roi_img, caption="Citra ROI (Area yang Diprediksi)", use_column_width=True)
            with col2:
                st.image(final_img, caption="Prediksi dengan Overlay ROI", use_column_width=True)
                st.metric("Estimasi Jumlah Orang", count)
                st.json({ "Koordinat ROI": roi_polygon.tolist() })

        except Exception as e:
            st.error(f"Gagal mengambil gambar: {e}")
        finally:
            if driver:
                driver.quit()
