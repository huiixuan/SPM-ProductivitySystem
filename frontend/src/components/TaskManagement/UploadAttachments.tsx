import { useRef } from "react"
import { Button } from "@/components/ui/button"
import { Trash2 } from "lucide-react"

type FormAttachment = File | { id: number; filename: string }

type UploadAttachmentsProps = {
  value?: FormAttachment[],
  onChange: (files: FormAttachment[]) => void
}

export default function UploadAttachments({ value = [], onChange }: UploadAttachmentsProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return

    const files = Array.from(e.target.files)
    onChange([...value, ...files])
  }

  const handleDelete = (index: number) => {
    const newFiles = [...value]
    newFiles.splice(index, 1)
    onChange(newFiles)
  }

  return (
    <div className="overscroll-auto mb-2">
      <input ref={fileInputRef} type="file" accept="application/pdf" multiple onChange={handleFileChange} className="hidden" />
      <Button type="button" onClick={() => fileInputRef.current?.click()}>Upload PDFs</Button>
    
      {value.length > 0 && (
        <div className="overflow-y-auto max-h-17 mt-1 border border-gray-300 border-dashed p-2 rounded">
          <p className="text-sm font-semibold">Attached Files:</p>
          {value.map((file, idx) => (
            <div key={idx} className="flex flex-row gap-2">
              <a href={file instanceof File ? URL.createObjectURL(file) : `/api/attachment/get-attachment/${file.id}`} target="_blank" rel="noopener noreferrer">
                {file instanceof File ? file.name : file.filename}
              </a>
              
              <Trash2 onClick={() => handleDelete(idx)} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}