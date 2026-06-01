import type { PlaygroundImageContentPart } from "../../../api/playgrounds";
import AttachmentImage from "./AttachmentImage";
import ImageDownloadButton from "./ImageDownloadButton";

type ImageViewerProps = {
  image: PlaygroundImageContentPart | null;
  onClose: () => void;
};

export default function ImageViewer({ image, onClose }: ImageViewerProps): JSX.Element | null {
  if (!image) {
    return null;
  }

  return (
    <div className="chatbot-image-viewer" role="dialog" aria-modal="true" aria-label="Image preview">
      <div className="chatbot-image-viewer-backdrop" onClick={onClose} />
      <div className="chatbot-image-viewer-panel">
        <AttachmentImage image={image} className="chatbot-image-viewer-image" />
        <div className="chatbot-image-viewer-actions">
          <ImageDownloadButton image={image} className="btn btn-secondary chatbot-image-viewer-download" label="Download" />
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
