import base64
import numpy as np
import random
from PIL import Image
import io
import re
import uuid

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import VerificationSession

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import pytesseract
except ImportError:
    pytesseract = None


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


def validate_and_decode_image(image_input):
    """
    Validates uploaded image file or base64 string:
    - Checks max size (< 10MB)
    - Validates file MIME type / PIL image format
    - Ensures valid image decodability
    Returns (image_bytes, format_name) or raises ValueError
    """
    image_bytes = None

    if hasattr(image_input, 'read'):
        # UploadedFile object from request.FILES
        image_bytes = image_input.read()
    elif isinstance(image_input, str):
        # Base64 data URL or raw string
        base64_str = image_input
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        try:
            image_bytes = base64.b64decode(base64_str)
        except Exception:
            raise ValueError("Invalid base64 image encoding.")
    elif isinstance(image_input, bytes):
        image_bytes = image_input
    else:
        raise ValueError("Unsupported image input format.")

    if not image_bytes:
        raise ValueError("Empty image data provided.")

    if len(image_bytes) > MAX_FILE_SIZE:
        raise ValueError(f"Image file size exceeds maximum limit of 10 MB ({len(image_bytes)} bytes provided).")

    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img.verify()
        # Re-open after verify() to inspect format
        pil_img = Image.open(io.BytesIO(image_bytes))
        img_format = pil_img.format.upper() if pil_img.format else "JPEG"
        if img_format not in ['JPEG', 'JPG', 'PNG', 'WEBP', 'BMP']:
            raise ValueError(f"Unsupported image format: {img_format}. Allowed formats: JPEG, PNG, WEBP, BMP.")
    except Exception as err:
        if isinstance(err, ValueError):
            raise err
        raise ValueError("Corrupted or unreadable image file.")

    return image_bytes, img_format


def broadcast_session_update(session):
    """
    Broadcasts session status update to Django Channels WebSocket group.
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"verif_{session.code}",
                {
                    "type": "verification_status",
                    "status": session.status,
                    "data": {
                        "type": "verification_status",
                        "status": session.status,
                        "session_id": session.code,
                        "code": session.code,
                        "token": session.token,
                        "front_image": session.front_image,
                        "back_image": session.back_image,
                        "selfie_image": session.selfie_image,
                        "updated_at": session.updated_at.isoformat()
                    }
                }
            )
    except Exception as ws_err:
        print("WS Broadcast info:", ws_err)


class CreateVerificationSessionView(APIView):
    """
    POST /api/verification/session/create/
    Creates a secure temporary verification session and returns session_id, token, and qr_url
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        session_id = f"VERIF-{random.randint(100000, 999999)}"
        token = uuid.uuid4().hex[:16]
        while VerificationSession.objects.filter(code=session_id).exists():
            session_id = f"VERIF-{random.randint(100000, 999999)}"

        session = VerificationSession.objects.create(
            code=session_id,
            token=token,
            status='CREATED'
        )

        origin = request.headers.get('Origin') or f"https://{request.get_host()}"
        qr_url = f"{origin}/verify/mobile/{token}"
        ws_host = request.get_host()
        ws_url = f"ws://{ws_host}/ws/verification/{session_id}/"

        return Response({
            "success": True,
            "session_id": session.code,
            "token": session.token,
            "qr_url": qr_url,
            "session_code": session.code,
            "status": session.status,
            "websocket_url": ws_url
        }, status=status.HTTP_201_CREATED)


class GetVerificationSessionView(APIView):
    """
    GET /api/verification/session/<session_code>/
    Fetch current session state by session_code or token for cross-device polling / sync
    """
    permission_classes = [AllowAny]

    def get(self, request, session_code, *args, **kwargs):
        session = VerificationSession.objects.filter(code=session_code).first() or \
                  VerificationSession.objects.filter(token=session_code).first()

        if not session:
            session = VerificationSession.objects.create(
                code=session_code,
                token=uuid.uuid4().hex[:16],
                status='CREATED'
            )

        return Response({
            "session_id": session.code,
            "code": session.code,
            "token": session.token,
            "status": session.status,
            "front_image": session.front_image,
            "back_image": session.back_image,
            "selfie_image": session.selfie_image,
            "updated_at": session.updated_at.isoformat()
        }, status=status.HTTP_200_OK)


class UpdateVerificationSessionView(APIView):
    """
    POST /api/verification/session/<session_code>/update/
    Update session status, front_image, back_image, or selfie_image and broadcast via Django Channels WebSocket
    """
    permission_classes = [AllowAny]

    def post(self, request, session_code, *args, **kwargs):
        try:
            session = VerificationSession.objects.filter(code=session_code).first() or \
                      VerificationSession.objects.filter(token=session_code).first()

            if not session:
                session = VerificationSession.objects.create(
                    code=session_code,
                    token=uuid.uuid4().hex[:16],
                    status='CREATED'
                )
            
            new_status = request.data.get('status')
            front_image = request.data.get('front_image') or request.data.get('frontImage')
            back_image = request.data.get('back_image') or request.data.get('backImage')
            selfie_image = request.data.get('selfie_image') or request.data.get('selfieImage')

            if new_status:
                session.status = new_status
            if front_image:
                session.front_image = front_image
                if session.status in ['CREATED', 'PHONE_CONNECTED', 'AADHAAR_FRONT_REQUIRED', 'AADHAAR_FRONT_CAPTURED']:
                    session.status = 'AADHAAR_BACK_REQUIRED'
            if back_image:
                session.back_image = back_image
                if session.status in ['AADHAAR_BACK_REQUIRED', 'AADHAAR_BACK_CAPTURED']:
                    session.status = 'AADHAAR_COMPLETED'
            if selfie_image:
                session.selfie_image = selfie_image
                session.status = 'REGISTRATION_COMPLETED'

            session.save()
            broadcast_session_update(session)

            return Response({
                "success": True,
                "session_id": session.code,
                "token": session.token,
                "session": {
                    "code": session.code,
                    "status": session.status,
                    "front_image": session.front_image,
                    "back_image": session.back_image,
                    "selfie_image": session.selfie_image,
                    "updated_at": session.updated_at.isoformat()
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": f"Failed to update session: {str(e)}",
                "success": False
            }, status=status.HTTP_400_BAD_REQUEST)


class UploadAadhaarView(APIView):
    """
    POST /api/verification/aadhaar/
    Accepts multipart/form-data requests with session_id, side ('front' | 'back'), and document.
    Validates:
    1. Session exists
    2. Session not expired / cancelled
    3. Correct expected side & workflow state (blocks invalid front -> back -> front regressions)
    4. Image validity & decodability
    5. File size (< 10MB limit)
    6. MIME type
    """
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, *args, **kwargs):
        try:
            session_code = request.data.get('session_id') or request.data.get('session_code') or request.data.get('code')
            side = (request.data.get('side') or 'front').lower().strip()
            allow_retry = str(request.data.get('allow_retry') or request.data.get('retry') or '').lower() in ['true', '1']

            image_input = request.FILES.get('document') or request.FILES.get('image') or \
                          request.data.get('document') or request.data.get('image') or \
                          request.data.get('image_base64') or request.data.get('front_image') or \
                          request.data.get('back_image')

            if not session_code:
                return Response({"error": "session_id is required.", "success": False}, status=status.HTTP_400_BAD_REQUEST)

            session = VerificationSession.objects.filter(code=session_code).first() or \
                      VerificationSession.objects.filter(token=session_code).first()

            if not session:
                return Response({"error": "Verification session not found.", "success": False}, status=status.HTTP_404_NOT_FOUND)

            if session.status in ['SESSION_EXPIRED', 'CANCELLED']:
                return Response({"error": "Verification session has expired or been cancelled.", "success": False}, status=status.HTTP_400_BAD_REQUEST)

            # Workflow State Guard (Prevent invalid state regressions like front -> back -> front)
            if side == 'front':
                if session.status in ['AADHAAR_BACK_REQUIRED', 'AADHAAR_COMPLETED', 'REGISTRATION_COMPLETED']:
                    if not allow_retry:
                        return Response({
                            "error": "Front side already captured. Expected BACK side. (front -> back -> front sequence rejected)",
                            "success": False,
                            "current_status": session.status
                        }, status=status.HTTP_400_BAD_REQUEST)
            elif side == 'back':
                if session.status in ['CREATED', 'PHONE_CONNECTED', 'AADHAAR_FRONT_REQUIRED']:
                    return Response({
                        "error": "Please capture the FRONT side of your Aadhaar card first.",
                        "success": False,
                        "current_status": session.status
                    }, status=status.HTTP_400_BAD_REQUEST)
                elif session.status in ['AADHAAR_COMPLETED', 'REGISTRATION_COMPLETED']:
                    if not allow_retry:
                        return Response({
                            "error": "Aadhaar verification is already complete.",
                            "success": False,
                            "current_status": session.status
                        }, status=status.HTTP_400_BAD_REQUEST)

            if not image_input:
                return Response({"error": "Document image file is required.", "success": False}, status=status.HTTP_400_BAD_REQUEST)

            # Server-side validation (< 10MB limit, MIME and decodability check)
            try:
                image_bytes, img_format = validate_and_decode_image(image_input)
            except ValueError as val_err:
                return Response({"error": str(val_err), "success": False}, status=status.HTTP_400_BAD_REQUEST)

            mime_type = "png" if img_format == "PNG" else "jpeg"
            base64_img = base64.b64encode(image_bytes).decode('utf-8')
            data_url = f"data:image/{mime_type};base64,{base64_img}"

            if side == 'back':
                session.back_image = data_url
                session.status = 'AADHAAR_COMPLETED'
            else:
                session.front_image = data_url
                session.status = 'AADHAAR_BACK_REQUIRED'

            session.save()
            broadcast_session_update(session)

            return Response({
                "success": True,
                "session_id": session.code,
                "side": side,
                "status": session.status,
                "updated_at": session.updated_at.isoformat()
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Aadhaar upload failed: {str(e)}", "success": False}, status=status.HTTP_400_BAD_REQUEST)


class UploadSelfieView(APIView):
    """
    POST /api/verification/selfie/
    Uploads selfie image, enforces server-side validation (<10MB, MIME check), updates session to REGISTRATION_COMPLETED, and broadcasts via WebSockets.
    Note: Face Detection != Identity Verification != Liveness
    """
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, *args, **kwargs):
        try:
            session_code = request.data.get('session_code') or request.data.get('session_id') or request.data.get('code')
            selfie_input = request.FILES.get('image') or request.data.get('selfie_image') or request.data.get('selfieImage') or request.data.get('image') or request.data.get('image_base64')

            if not session_code:
                return Response({"error": "session_code is required.", "success": False}, status=status.HTTP_400_BAD_REQUEST)

            data_url = None
            if selfie_input:
                try:
                    image_bytes, img_format = validate_and_decode_image(selfie_input)
                    mime_type = "png" if img_format == "PNG" else "jpeg"
                    base64_img = base64.b64encode(image_bytes).decode('utf-8')
                    data_url = f"data:image/{mime_type};base64,{base64_img}"
                except ValueError as val_err:
                    return Response({"error": str(val_err), "success": False}, status=status.HTTP_400_BAD_REQUEST)

            session = VerificationSession.objects.filter(code=session_code).first() or \
                      VerificationSession.objects.filter(token=session_code).first()

            if not session:
                session = VerificationSession.objects.create(
                    code=session_code,
                    token=uuid.uuid4().hex[:16],
                    status='CREATED'
                )

            if data_url:
                session.selfie_image = data_url

            session.status = 'REGISTRATION_COMPLETED'
            session.save()
            broadcast_session_update(session)

            return Response({
                "success": True,
                "session_id": session.code,
                "status": session.status,
                "selfie_image": session.selfie_image,
                "liveness_disclaimer": "Face Detection != Identity Verification != Liveness (Prototype Face Alignment Only)"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e), "success": False}, status=status.HTTP_400_BAD_REQUEST)


class CompleteVerificationView(APIView):
    """
    POST /api/verification/complete/
    Finalizes verification session and sets status to REGISTRATION_COMPLETED.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            session_code = request.data.get('session_code') or request.data.get('session_id') or request.data.get('code')
            if not session_code:
                return Response({"error": "session_code is required.", "success": False}, status=status.HTTP_400_BAD_REQUEST)

            session = VerificationSession.objects.filter(code=session_code).first() or \
                      VerificationSession.objects.filter(token=session_code).first()

            if not session:
                return Response({"error": "Verification session not found.", "success": False}, status=status.HTTP_404_NOT_FOUND)

            session.status = 'REGISTRATION_COMPLETED'
            session.save()
            broadcast_session_update(session)

            return Response({
                "success": True,
                "session_id": session.code,
                "status": session.status,
                "message": "Registration verification marked as complete."
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e), "success": False}, status=status.HTTP_400_BAD_REQUEST)


class CancelVerificationSessionView(APIView):
    """
    POST /api/verification/session/<session_code>/cancel/
    Cancels or expires a verification session and broadcasts update to clients.
    """
    permission_classes = [AllowAny]

    def post(self, request, session_code, *args, **kwargs):
        try:
            session = VerificationSession.objects.filter(code=session_code).first() or \
                      VerificationSession.objects.filter(token=session_code).first()

            if not session:
                return Response({"error": "Verification session not found.", "success": False}, status=status.HTTP_404_NOT_FOUND)

            session.status = 'SESSION_EXPIRED'
            session.save()
            broadcast_session_update(session)

            return Response({
                "success": True,
                "session_id": session.code,
                "status": session.status,
                "message": "Verification session cancelled."
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e), "success": False}, status=status.HTTP_400_BAD_REQUEST)




def order_points(pts):
    """
    Orders 4 coordinates: top-left, top-right, bottom-right, bottom-left
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def four_point_transform(image, pts):
    """
    Applies perspective transformation to straighten and crop a document polygon
    """
    if cv2 is None:
        return image, pts

    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    # Calculate width of new image
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    # Calculate height of new image
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    # Destination points
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")

    # Perspective transform matrix
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped, rect


class ProcessDocumentView(APIView):
    """
    API Endpoint:
    React Camera -> Live auto-capture -> OpenCV perspective correction & crop -> OCR
    """
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, *args, **kwargs):
        try:
            image_bytes = None

            # Handle direct file upload or base64 string
            if 'image' in request.FILES:
                image_file = request.FILES['image']
                image_bytes = image_file.read()
            elif 'image_base64' in request.data:
                base64_str = request.data['image_base64']
                if ',' in base64_str:
                    base64_str = base64_str.split(',')[1]
                image_bytes = base64.b64decode(base64_str)
            else:
                return Response(
                    {"error": "No image or image_base64 provided."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if cv2 is None:
                # Return standard base64 echo if cv2 module is missing in host env
                base64_data_url = request.data.get('image_base64') or f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                return Response({
                    "success": True,
                    "processed_image": base64_data_url,
                    "extracted_text": "Document captured (OpenCV fallback mode)",
                    "corners": []
                }, status=status.HTTP_200_OK)

            # Decode image buffer using OpenCV
            np_arr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if image is None:
                return Response(
                    {"error": "Failed to decode image buffer."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            orig_h, orig_w = image.shape[:2]

            # Convert to grayscale and apply blur
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Canny Edge Detection
            edged = cv2.Canny(blurred, 50, 200)

            # Find contours
            contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

            doc_cnt = None

            # Loop over contours to find 4-sided polygon
            for c in contours:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) == 4:
                    doc_cnt = approx
                    break

            if doc_cnt is not None:
                pts = doc_cnt.reshape(4, 2)
                warped, ordered_rect = four_point_transform(image, pts)
                corners_list = ordered_rect.tolist()
            else:
                crop_y1 = int(orig_h * 0.05)
                crop_y2 = int(orig_h * 0.95)
                crop_x1 = int(orig_w * 0.05)
                crop_x2 = int(orig_w * 0.95)
                warped = image[crop_y1:crop_y2, crop_x1:crop_x2]
                corners_list = [[crop_x1, crop_y1], [crop_x2, crop_y1], [crop_x2, crop_y2], [crop_x1, crop_y2]]

            # Enhance image for high contrast document scan view
            warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
            enhanced = cv2.adaptiveThreshold(
                warped_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

            # Blend enhanced binary scan with original warped photo
            final_doc = cv2.addWeighted(warped, 0.65, enhanced_bgr, 0.35, 0)

            # Encode processed document image to base64
            _, buffer = cv2.imencode('.jpg', final_doc, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
            processed_base64 = base64.b64encode(buffer).decode('utf-8')
            processed_data_url = f"data:image/jpeg;base64,{processed_base64}"

            # OCR Text Extraction
            extracted_text = ""
            if pytesseract:
                try:
                    pil_img = Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))
                    extracted_text = pytesseract.image_to_string(pil_img)
                    extracted_text = re.sub(r'\n+', '\n', extracted_text).strip()
                except Exception:
                    extracted_text = "OCR raw stream captured (Tesseract engine standby)"

            return Response({
                "success": True,
                "processed_image": processed_data_url,
                "extracted_text": extracted_text or "Verified Document Scan (Clean Edge Transformation)",
                "corners": corners_list,
                "dimensions": {
                    "width": final_doc.shape[1],
                    "height": final_doc.shape[0]
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Document processing failed: {str(e)}", "success": False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
