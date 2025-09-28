import { useRef } from "react"
import { Button } from "@/components/ui/button"

type UploadAttachmentsProps = {
    value?: File[],
    onChange: (files: File[]) => void
}

export default function UploadAttachments({ value = [], onChange }: UploadAttachmentsProps) {
    const fileInputRef = useRef<HTMLInputElement>(null)

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files) return

        const files = Array.from(e.target.files)
        onChange([...value, ...files])
    }

    const displayFiles = value.slice(0, 2)
    const extraCount = value.length - displayFiles.length

    return (
        <div>
            <input ref={fileInputRef} type="file" accept="application/pdf" multiple onChange={handleFileChange} className="hidden" />
            <Button type="button" onClick={() => fileInputRef.current?.click()}>Upload PDFs</Button>

            {value.length > 0 && (
                <ul className="list-disc list-inside">
                    {displayFiles.map((file, idx) => (
                        <li key={idx}>{file.name}</li>
                    ))}
                    {extraCount > 0 && <p>... {extraCount} more</p>}
                </ul>
            )}
        </div>
    )
}