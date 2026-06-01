import { useAuth } from "../../../auth/AuthProvider";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import type { PlaygroundImageContentPart } from "../../../api/playgrounds";
import { downloadAttachmentImage } from "./AttachmentImage";

type ImageDownloadButtonProps = {
  image: PlaygroundImageContentPart;
  className?: string;
  label?: string;
};

export default function ImageDownloadButton({
  image,
  className = "chatbot-image-download",
  label = "Download image",
}: ImageDownloadButtonProps): JSX.Element {
  const { token } = useAuth();
  const { showErrorFeedback } = useActionFeedback();

  return (
    <button
      type="button"
      className={className}
      aria-label={label}
      title={label}
      onClick={() => {
        if (!token) {
          return;
        }
        void downloadAttachmentImage(image, token).catch((error) => {
          showErrorFeedback(error, "Image download failed");
        });
      }}
    >
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M12 4v10m0 0 4-4m-4 4-4-4M5 20h14" />
      </svg>
      <span className="sr-only">{label}</span>
    </button>
  );
}
