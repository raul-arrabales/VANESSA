import type { PlaygroundImageContentPart } from "../../../api/playgrounds";
import AttachmentImage from "./AttachmentImage";
import ImageDownloadButton from "./ImageDownloadButton";

type MessageImageGridProps = {
  images: PlaygroundImageContentPart[];
  onOpenImage: (image: PlaygroundImageContentPart) => void;
};

export default function MessageImageGrid({ images, onOpenImage }: MessageImageGridProps): JSX.Element | null {
  if (images.length === 0) {
    return null;
  }

  return (
    <div className="chatbot-message-images" aria-label="Attached images">
      {images.map((image) => (
        <figure key={image.image_ref} className="chatbot-message-image">
          <AttachmentImage
            image={image}
            className="chatbot-message-image-button"
            onClick={() => onOpenImage(image)}
          />
          <ImageDownloadButton image={image} />
        </figure>
      ))}
    </div>
  );
}
