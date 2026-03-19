import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";
import { useRuntimeMode } from "../runtime/RuntimeModeProvider";
import type { RuntimeProfile } from "../api/runtime";

const PROFILE_OPTIONS: RuntimeProfile[] = ["offline", "online"];

export default function RuntimeProfileSection(): JSX.Element {
  const { t } = useTranslation("common");
  const { user } = useAuth();
  const { mode, isLocked, isLoading, isSaving, error, setMode } = useRuntimeMode();
  const isSuperadmin = user?.role === "superadmin";
  const [statusMessage, setStatusMessage] = useState<string>("");
  const isFieldsetDisabled = isLoading || isSaving || !isSuperadmin || isLocked;

  const onChangeProfile = async (nextProfile: RuntimeProfile): Promise<void> => {
    if (!isSuperadmin || isLocked) {
      return;
    }

    setStatusMessage("");

    try {
      const updatedProfile = await setMode(nextProfile);
      setStatusMessage(t("settings.runtime.feedback.saved", { profile: t(`settings.runtime.options.${updatedProfile}`) }));
    } catch {
      // Error state comes from RuntimeModeProvider.
    }
  };

  return (
    <section className="card-stack" aria-label={t("settings.runtime.title")}>
      <h3 className="section-title">{t("settings.runtime.title")}</h3>
      <p className="status-text">{t("settings.runtime.description")}</p>
      <fieldset
        className="card-stack"
        disabled={isFieldsetDisabled}
        title={!isSuperadmin ? t("settings.runtime.restrictionMessage") : isLocked ? t("settings.runtime.lockedMessage") : undefined}
      >
        {PROFILE_OPTIONS.map((option) => (
          <label key={option}>
            <input
              type="radio"
              name="runtime-profile"
              value={option}
              checked={mode === option}
              onChange={() => {
                void onChangeProfile(option);
              }}
            />{" "}
            {t(`settings.runtime.options.${option}`)}
          </label>
        ))}
      </fieldset>
      {!isSuperadmin && <p className="status-text">{t("settings.runtime.restrictionMessage")}</p>}
      {isLocked && <p className="status-text">{t("settings.runtime.lockedMessage")}</p>}
      {statusMessage && <p className="status-text">{statusMessage}</p>}
      {error && <p className="status-text">{error === "runtimeMode.updateFailed" ? t("runtimeMode.updateFailed") : error}</p>}
    </section>
  );
}
