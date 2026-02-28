import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";
import { ApiError, fetchRuntimeProfile, updateRuntimeProfile } from "../auth/authApi";

type RuntimeProfile = "offline" | "air_gapped" | "online";

const PROFILE_OPTIONS: RuntimeProfile[] = ["offline", "air_gapped", "online"];

export default function RuntimeProfileSection(): JSX.Element {
  const { t } = useTranslation("common");
  const { token, user } = useAuth();
  const isSuperadmin = user?.role === "superadmin";
  const [profile, setProfile] = useState<RuntimeProfile | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  useEffect(() => {
    if (!token) {
      return;
    }

    setIsLoading(true);
    setErrorMessage("");
    fetchRuntimeProfile(token)
      .then((result) => {
        setProfile(result.profile);
      })
      .catch((error: unknown) => {
        const message = error instanceof ApiError ? error.message : t("settings.runtime.error.load");
        setErrorMessage(message);
      })
      .finally(() => setIsLoading(false));
  }, [token, t]);

  const onChangeProfile = async (nextProfile: RuntimeProfile): Promise<void> => {
    if (!isSuperadmin || !token) {
      return;
    }

    setIsSaving(true);
    setStatusMessage("");
    setErrorMessage("");

    try {
      const result = await updateRuntimeProfile(nextProfile, token);
      setProfile(result.profile);
      setStatusMessage(t("settings.runtime.feedback.saved", { profile: t(`settings.runtime.options.${result.profile}`) }));
    } catch (error: unknown) {
      const message = error instanceof ApiError ? error.message : t("settings.runtime.error.save");
      setErrorMessage(message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="card-stack" aria-label={t("settings.runtime.title")}>
      <h3 className="section-title">{t("settings.runtime.title")}</h3>
      <p className="status-text">{t("settings.runtime.description")}</p>
      <fieldset
        className="card-stack"
        disabled={isLoading || isSaving || !isSuperadmin}
        title={!isSuperadmin ? t("settings.runtime.restrictionMessage") : undefined}
      >
        {PROFILE_OPTIONS.map((option) => (
          <label key={option}>
            <input
              type="radio"
              name="runtime-profile"
              value={option}
              checked={profile === option}
              onChange={() => {
                void onChangeProfile(option);
              }}
            />{" "}
            {t(`settings.runtime.options.${option}`)}
          </label>
        ))}
      </fieldset>
      {!isSuperadmin && <p className="status-text">{t("settings.runtime.restrictionMessage")}</p>}
      {statusMessage && <p className="status-text">{statusMessage}</p>}
      {errorMessage && <p className="status-text">{errorMessage}</p>}
    </section>
  );
}
