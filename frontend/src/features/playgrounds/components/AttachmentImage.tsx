import { useEffect, useState } from "react";
import { buildUrl } from "../../../auth/authApi";
import { useAuth } from "../../../auth/AuthProvider";
import { playgroundAttachmentUrl, type PlaygroundImageContentPart } from "../../../api/playgrounds";

type AttachmentImageProps = {
  image: PlaygroundImageContentPart;
  className?: string;
  onClick?: () => void;
};

export default function AttachmentImage({ image, className, onClick }: AttachmentImageProps): JSX.Element {
  const { token } = useAuth();
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !image.image_ref) {
      return;
    }
    let isCancelled = false;
    let nextObjectUrl: string | null = null;
    void fetch(buildUrl(playgroundAttachmentUrl(image.image_ref)), {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("image_fetch_failed");
        }
        return response.blob();
      })
      .then((blob) => {
        if (isCancelled) {
          return;
        }
        nextObjectUrl = URL.createObjectURL(blob);
        setObjectUrl(nextObjectUrl);
      })
      .catch(() => {
        if (!isCancelled) {
          setObjectUrl(null);
        }
      });

    return () => {
      isCancelled = true;
      if (nextObjectUrl) {
        URL.revokeObjectURL(nextObjectUrl);
      }
    };
  }, [image.image_ref, token]);

  return (
    <button
      type="button"
      className={className}
      onClick={onClick}
      disabled={!objectUrl || !onClick}
      aria-label={image.alt_text || "Open image"}
    >
      {objectUrl ? (
        <img src={objectUrl} alt={image.alt_text || "Chat attachment"} />
      ) : (
        <span className="chatbot-image-placeholder">Image</span>
      )}
    </button>
  );
}

export async function downloadAttachmentImage(image: PlaygroundImageContentPart, token: string): Promise<void> {
  const response = await fetch(buildUrl(playgroundAttachmentUrl(image.image_ref, { download: true })), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error("image_download_failed");
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = `${image.image_ref.replace("attachment://", "image-attachment")}`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
