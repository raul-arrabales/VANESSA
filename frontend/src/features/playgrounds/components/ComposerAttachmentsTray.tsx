import type { PlaygroundImageContentPart } from "../../../api/playgrounds";
import AttachmentImage from "./AttachmentImage";

type ComposerAttachmentsTrayProps = {
  pendingImages: PlaygroundImageContentPart[];
  isSending: boolean;
  onRemoveImage?: (imageRef: string) => void;
};

export default function ComposerAttachmentsTray({
  pendingImages,
  isSending,
  onRemoveImage,
}: ComposerAttachmentsTrayProps): JSX.Element | null {
  if (pendingImages.length === 0) {
    return null;
  }

  return (
    <div className="chatbot-composer-attachments" aria-label="Images ready to send">
      {pendingImages.map((image) => (
        <figure key={image.image_ref} className="chatbot-composer-attachment">
          <AttachmentImage image={image} className="chatbot-composer-attachment-preview" />
          <button
            type="button"
            className="chatbot-composer-attachment-remove"
            onClick={() => onRemoveImage?.(image.image_ref)}
            aria-label="Remove image"
            disabled={isSending}
          >
            x
          </button>
        </figure>
      ))}
    </div>
  );
}
