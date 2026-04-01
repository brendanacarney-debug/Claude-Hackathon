"use client";

import { useCallback, useEffect, useState } from "react";

import { useCamera } from "@/hooks/useCamera";

interface CaptureStep {
  roomType: string;
  label: string;
  hint: string;
}

const steps: CaptureStep[] = [
  {
    roomType: "bedroom",
    label: "Bedroom",
    hint: "Stand in the doorway and capture the whole room, including the path to the door.",
  },
  {
    roomType: "bathroom",
    label: "Bathroom",
    hint: "Show the toilet, shower or tub, sink, and the floor between them.",
  },
  {
    roomType: "hallway",
    label: "Hallway",
    hint: "Capture the route from bedroom to bathroom and any obstacles along it.",
  },
];

interface Capture {
  file: File;
  roomType: string;
  url: string;
}

export function CaptureGuide({
  onComplete,
}: {
  onComplete: (photos: File[], roomTypes: string[]) => Promise<void>;
}) {
  const [stepIndex, setStepIndex] = useState(0);
  const [captures, setCaptures] = useState<Capture[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const {
    videoRef,
    state: cameraState,
    errorMessage,
    startCamera,
    stopCamera,
    capturePhoto,
  } = useCamera();

  const isComplete = stepIndex >= steps.length;
  const step = steps[stepIndex];

  useEffect(() => {
    if (isComplete) {
      return;
    }

    void startCamera();
    return () => stopCamera();
  }, [isComplete, startCamera, stepIndex, stopCamera]);

  const handleCapture = useCallback(async () => {
    const file = await capturePhoto();
    if (!file || !step) {
      return;
    }

    const url = URL.createObjectURL(file);
    setCaptures((current) => [...current, { file, roomType: step.roomType, url }]);
    stopCamera();
    setStepIndex((current) => current + 1);
  }, [capturePhoto, step, stopCamera]);

  const handleFileUpload = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file || !step) {
        return;
      }

      const url = URL.createObjectURL(file);
      setCaptures((current) => [...current, { file, roomType: step.roomType, url }]);
      stopCamera();
      setStepIndex((current) => current + 1);
      event.target.value = "";
    },
    [step, stopCamera],
  );

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitError(null);

    try {
      await onComplete(
        captures.map((capture) => capture.file),
        captures.map((capture) => capture.roomType),
      );
    } catch (cause) {
      setSubmitError(
        cause instanceof Error
          ? cause.message
          : "Upload failed. Please try again.",
      );
      setSubmitting(false);
    }
  }

  if (isComplete) {
    return (
      <div className="space-y-5">
        <div>
          <h2 className="text-base font-semibold text-slate-800">
            Review Your Photos
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            All three rooms are captured. Select &ldquo;Analyze&rdquo; to continue.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-3">
          {captures.map((capture, index) => (
            <div
              key={`${capture.roomType}-${index}`}
              className="relative aspect-square overflow-hidden rounded-xl bg-slate-100"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={capture.url}
                alt={`${capture.roomType} capture`}
                className="h-full w-full object-cover"
              />
              <span className="absolute inset-x-0 bottom-0 bg-black/55 py-1 text-center text-xs font-medium text-white">
                {steps[index]?.label ?? capture.roomType}
              </span>
            </div>
          ))}
        </div>

        {submitError ? (
          <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
            {submitError}
          </p>
        ) : null}

        <button
          type="button"
          onClick={handleSubmit}
          disabled={submitting}
          className="w-full rounded-xl bg-blue-600 py-3.5 text-sm font-semibold text-white transition-all hover:bg-blue-700 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Uploading..." : "Analyze Home"}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-1.5">
        {steps.map((currentStep, index) => (
          <div
            key={currentStep.roomType}
            className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${
              index < stepIndex
                ? "bg-blue-500"
                : index === stepIndex
                  ? "bg-blue-300"
                  : "bg-slate-200"
            }`}
          />
        ))}
      </div>

      <div>
        <p className="text-xs font-semibold tracking-widest text-slate-400 uppercase">
          Step {stepIndex + 1} of {steps.length}
        </p>
        <h2 className="mt-0.5 text-lg font-semibold text-slate-800">{step.label}</h2>
        <p className="mt-1 text-sm leading-relaxed text-slate-500">{step.hint}</p>
      </div>

      <div className="relative aspect-video overflow-hidden rounded-xl bg-slate-900">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="h-full w-full object-cover"
        />

        {cameraState === "starting" ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-sm text-white">Starting camera...</p>
          </div>
        ) : null}

        {cameraState === "denied" || cameraState === "error" ? (
          <div className="absolute inset-0 flex items-center justify-center px-6 text-center">
            <p className="text-sm leading-relaxed text-white">
              {errorMessage ?? "Camera unavailable. Use file upload below."}
            </p>
          </div>
        ) : null}
      </div>

      {captures.length > 0 ? (
        <div className="flex gap-2">
          {captures.map((capture, index) => (
            <div
              key={`${capture.roomType}-thumb-${index}`}
              className="h-12 w-12 flex-shrink-0 overflow-hidden rounded-lg bg-slate-200 ring-2 ring-emerald-400"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={capture.url}
                alt={`${capture.roomType} thumbnail`}
                className="h-full w-full object-cover"
              />
            </div>
          ))}
        </div>
      ) : null}

      <button
        type="button"
        onClick={handleCapture}
        disabled={cameraState !== "ready"}
        className="w-full rounded-xl bg-blue-600 py-3.5 text-sm font-semibold text-white transition-all hover:bg-blue-700 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {cameraState === "starting"
          ? "Starting..."
          : `Take Photo - ${step.label}`}
      </button>

      <label className="flex cursor-pointer items-center justify-center gap-2 text-xs text-slate-400 transition-colors hover:text-slate-600">
        <svg
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 20 20"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4 16l4-4 3 3 3-4 4 5H4z M4 4h12"
          />
        </svg>
        Or upload a photo from your device
        <input
          type="file"
          accept="image/*"
          className="sr-only"
          onChange={handleFileUpload}
        />
      </label>
    </div>
  );
}
