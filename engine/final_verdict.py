def generate_final_verdict(segments, results, frame_dir, output_path):
    """
    Generates a human-readable final verdict report for the video.
    Each segment is analysed independently and written in order.
    """

    # Open the output file where the final report will be written
    with open(output_path, "w", encoding="utf-8") as f:

        # Write report header
        f.write("FINAL ANALYSIS REPORT\n")
        f.write("=" * 50 + "\n\n")

        # Loop through each segment and its corresponding score
        for idx, (seg, res) in enumerate(zip(segments, results), start=1):

            # Segment basic information
            f.write(f"SEGMENT {idx}\n")
            f.write(
                f"Time: {seg['startTime']:.2f}s → {seg['endTime']:.2f}s\n"
            )
            f.write(
                f"Frames: {seg['frames'][0]} → {seg['frames'][-1]}\n\n"
            )

            # Write confidence scores computed during scoring phase
            f.write(
                f"Banking Context Confidence: "
                f"{res['bankingContextPercentage']}%\n"
            )
            f.write(
                f"Crypto Context Confidence: "
                f"{res['cryptoContextPercentage']}%\n"
            )
            f.write(
                f"Transaction Likely Confidence: "
                f"{res['transactionLikelyPercentage']}%\n"
            )
            f.write(
                f"Transaction Executed Confidence: "
                f"{res['transactionExecutedPercentage']}%\n"
            )

            # Check if QR code was detected in this segment
            qr_found = bool(seg.get("qrTexts"))

            # -------------------- VERDICT LOGIC --------------------

            # Case 1: Explicit transaction failure
            if res.get("transactionFailed"):
                verdict = "Transaction failed or incomplete"

            # Case 2: Strong execution confirmation
            elif res["transactionExecutedPercentage"] >= 85:
                verdict = "Transaction execution confirmed"

            # Case 3: Soft execution confirmation
            elif res["transactionExecutedPercentage"] >= 70:
                verdict = "Transaction executed (soft confirmation)"

            # Case 4: Transaction likely with QR evidence
            elif (
                res["transactionLikelyPercentage"] >= 60
                and qr_found
            ):
                verdict = (
                    "Transaction flow or payment initiation likely "
                    "(QR code detected)"
                )

            # Case 5: Transaction likely without QR
            elif res["transactionLikelyPercentage"] >= 60:
                verdict = "Transaction flow or payment initiation likely"

            # Case 6: Crypto-dominant interface detected
            elif (
                res["cryptoContextPercentage"] >= 30
                and res["cryptoContextPercentage"]
                > res["bankingContextPercentage"]
            ):
                verdict = "Crypto platform or trading interface detected"

            # Case 7: Banking interface detected
            elif res["bankingContextPercentage"] >= 30:
                verdict = "Banking or financial application context detected"

            # Case 8: No meaningful financial signals
            else:
                verdict = "No meaningful financial activity detected"

            # Write the final verdict for this segment
            f.write(f"Verdict: {verdict}\n")

            # Separator between segments
            f.write("-" * 50 + "\n\n")
